"""add preorders and phone auth

Revision ID: 2f7d9c1a8b44
Revises: c3b9aa1e5f20
Create Date: 2026-02-20 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2f7d9c1a8b44'
down_revision = 'c3b9aa1e5f20'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('users', sa.Column('phone', sa.String(length=20), nullable=True))

    op.execute("""
        UPDATE users
        SET phone = CASE
            WHEN is_admin = 1 THEN '+7-999-999-99-99'
            ELSE '+7-900-000-00-' || printf('%02d', id)
        END
        WHERE phone IS NULL OR phone = ''
    """)

    with op.batch_alter_table('users') as batch_op:
        batch_op.alter_column('email', existing_type=sa.String(length=120), nullable=True)
        batch_op.alter_column('phone', existing_type=sa.String(length=20), nullable=False)
        batch_op.create_unique_constraint('uq_users_phone', ['phone'])

    op.create_table(
        'preorders',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('comment', sa.Text(), nullable=True),
        sa.Column('pickup_time', sa.String(length=5), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_preorders_created_at'), 'preorders', ['created_at'], unique=False)
    op.create_index(op.f('ix_preorders_user_id'), 'preorders', ['user_id'], unique=False)

    op.create_table(
        'preorder_items',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('preorder_id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('quantity', sa.Numeric(precision=10, scale=3), nullable=False),
        sa.ForeignKeyConstraint(['preorder_id'], ['preorders.id']),
        sa.ForeignKeyConstraint(['product_id'], ['products.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_preorder_items_preorder_id'), 'preorder_items', ['preorder_id'], unique=False)
    op.create_index(op.f('ix_preorder_items_product_id'), 'preorder_items', ['product_id'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_preorder_items_product_id'), table_name='preorder_items')
    op.drop_index(op.f('ix_preorder_items_preorder_id'), table_name='preorder_items')
    op.drop_table('preorder_items')

    op.drop_index(op.f('ix_preorders_user_id'), table_name='preorders')
    op.drop_index(op.f('ix_preorders_created_at'), table_name='preorders')
    op.drop_table('preorders')

    with op.batch_alter_table('users') as batch_op:
        batch_op.drop_constraint('uq_users_phone', type_='unique')
        batch_op.alter_column('phone', existing_type=sa.String(length=20), nullable=True)
        batch_op.alter_column('email', existing_type=sa.String(length=120), nullable=False)

    op.drop_column('users', 'phone')
