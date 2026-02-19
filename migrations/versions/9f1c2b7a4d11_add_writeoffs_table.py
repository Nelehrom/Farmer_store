"""add writeoffs table

Revision ID: 9f1c2b7a4d11
Revises: 60e793aa6adb
Create Date: 2026-02-19 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9f1c2b7a4d11'
down_revision = '60e793aa6adb'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'write_offs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('quantity', sa.Numeric(precision=10, scale=3), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['product_id'], ['products.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_write_offs_created_at'), 'write_offs', ['created_at'], unique=False)
    op.create_index(op.f('ix_write_offs_product_id'), 'write_offs', ['product_id'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_write_offs_product_id'), table_name='write_offs')
    op.drop_index(op.f('ix_write_offs_created_at'), table_name='write_offs')
    op.drop_table('write_offs')
