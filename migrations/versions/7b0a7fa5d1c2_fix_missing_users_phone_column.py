"""fix missing users.phone column

Revision ID: 7b0a7fa5d1c2
Revises: 2f7d9c1a8b44
Create Date: 2026-02-20 12:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7b0a7fa5d1c2'
down_revision = '2f7d9c1a8b44'
branch_labels = None
depends_on = None


def _build_phone(user_id: int, is_admin: bool) -> str:
    if is_admin:
        return '+7-999-999-99-99'
    return f"+7-900-000-00-{user_id:02d}"


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col['name'] for col in inspector.get_columns('users')}

    if 'phone' not in columns:
        op.add_column('users', sa.Column('phone', sa.String(length=20), nullable=True))

    rows = bind.execute(
        sa.text("SELECT id, is_admin FROM users WHERE phone IS NULL OR phone = ''")
    ).fetchall()
    for row in rows:
        bind.execute(
            sa.text("UPDATE users SET phone = :phone WHERE id = :user_id"),
            {'phone': _build_phone(row.id, bool(row.is_admin)), 'user_id': row.id},
        )

    with op.batch_alter_table('users') as batch_op:
        batch_op.alter_column('email', existing_type=sa.String(length=120), nullable=True)
        batch_op.alter_column('phone', existing_type=sa.String(length=20), nullable=False)

    inspector = sa.inspect(bind)
    unique_constraints = {uc['name'] for uc in inspector.get_unique_constraints('users') if uc.get('name')}
    if 'uq_users_phone' not in unique_constraints:
        with op.batch_alter_table('users') as batch_op:
            batch_op.create_unique_constraint('uq_users_phone', ['phone'])


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    unique_constraints = {uc['name'] for uc in inspector.get_unique_constraints('users') if uc.get('name')}
    with op.batch_alter_table('users') as batch_op:
        if 'uq_users_phone' in unique_constraints:
            batch_op.drop_constraint('uq_users_phone', type_='unique')
        batch_op.alter_column('email', existing_type=sa.String(length=120), nullable=False)

    columns = {col['name'] for col in inspector.get_columns('users')}
    if 'phone' in columns:
        with op.batch_alter_table('users') as batch_op:
            batch_op.drop_column('phone')
