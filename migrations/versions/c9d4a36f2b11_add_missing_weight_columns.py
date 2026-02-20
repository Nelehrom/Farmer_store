"""add missing weight columns

Revision ID: c9d4a36f2b11
Revises: 8477ee04eaed
Create Date: 2026-02-19 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c9d4a36f2b11'
down_revision = '8477ee04eaed'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col['name'] for col in inspector.get_columns('products')}

    if 'min_weight' not in columns:
        op.add_column('products', sa.Column('min_weight', sa.Integer(), nullable=True))

    if 'max_weight' not in columns:
        op.add_column('products', sa.Column('max_weight', sa.Integer(), nullable=True))


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col['name'] for col in inspector.get_columns('products')}

    if 'max_weight' in columns:
        op.drop_column('products', 'max_weight')

    if 'min_weight' in columns:
        op.drop_column('products', 'min_weight')
