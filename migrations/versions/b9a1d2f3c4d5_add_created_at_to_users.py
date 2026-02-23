"""add created_at to users

Revision ID: b9a1d2f3c4d5
Revises: a1d2e3f4b5c6
Create Date: 2026-02-23 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b9a1d2f3c4d5'
down_revision = 'a1d2e3f4b5c6'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('users') as batch_op:
        batch_op.add_column(sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.text('CURRENT_TIMESTAMP')))

    bind = op.get_bind()
    bind.execute(sa.text("UPDATE users SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL"))

    with op.batch_alter_table('users') as batch_op:
        batch_op.alter_column('created_at', existing_type=sa.DateTime(), nullable=False)
        batch_op.create_index('ix_users_created_at', ['created_at'], unique=False)


def downgrade():
    with op.batch_alter_table('users') as batch_op:
        batch_op.drop_index('ix_users_created_at')
        batch_op.drop_column('created_at')
