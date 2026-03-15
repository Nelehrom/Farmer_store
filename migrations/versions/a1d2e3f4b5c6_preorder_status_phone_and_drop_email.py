"""preorder status phone normalization and drop email

Revision ID: a1d2e3f4b5c6
Revises: 7b0a7fa5d1c2
Create Date: 2026-02-20 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from datetime import date
import re


# revision identifiers, used by Alembic.
revision = 'a1d2e3f4b5c6'
down_revision = '7b0a7fa5d1c2'
branch_labels = None
depends_on = None


def _normalize_phone(phone_raw):
    digits = re.sub(r"\D", "", phone_raw or "")
    if len(digits) == 11 and digits.startswith("8"):
        digits = f"7{digits[1:]}"
    if len(digits) == 10:
        digits = f"7{digits}"
    if len(digits) != 11 or not digits.startswith("7"):
        return None
    return f"+{digits}"


def upgrade():
    bind = op.get_bind()

    with op.batch_alter_table('preorders') as batch_op:
        batch_op.add_column(sa.Column('pickup_date', sa.Date(), nullable=True))
        batch_op.add_column(sa.Column('status', sa.String(length=20), nullable=False, server_default='active'))
        batch_op.add_column(sa.Column('cancel_reason', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('completed_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('cancelled_at', sa.DateTime(), nullable=True))
        batch_op.create_index(batch_op.f('ix_preorders_status'), ['status'], unique=False)

    bind.execute(sa.text("UPDATE preorders SET pickup_date = :today WHERE pickup_date IS NULL"), {"today": date.today()})

    with op.batch_alter_table('preorders') as batch_op:
        batch_op.alter_column('pickup_date', existing_type=sa.Date(), nullable=False)

    rows = bind.execute(sa.text("SELECT id, phone FROM users")).fetchall()
    for row in rows:
        normalized = _normalize_phone(row.phone) or f"+7000000{row.id:04d}"
        bind.execute(sa.text("UPDATE users SET phone = :phone WHERE id = :user_id"), {"phone": normalized, "user_id": row.id})

    with op.batch_alter_table('users') as batch_op:
        batch_op.drop_constraint('uq_users_phone', type_='unique')
        batch_op.create_unique_constraint('uq_users_phone', ['phone'])
        batch_op.drop_column('email')


def downgrade():
    with op.batch_alter_table('users') as batch_op:
        batch_op.add_column(sa.Column('email', sa.String(length=120), nullable=True))

    with op.batch_alter_table('preorders') as batch_op:
        batch_op.drop_index(batch_op.f('ix_preorders_status'))
        batch_op.drop_column('cancelled_at')
        batch_op.drop_column('completed_at')
        batch_op.drop_column('cancel_reason')
        batch_op.drop_column('status')
        batch_op.drop_column('pickup_date')
