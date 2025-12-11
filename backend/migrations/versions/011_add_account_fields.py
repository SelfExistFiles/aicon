"""add is_default and login_status to bilibili_accounts

Revision ID: 011
Revises: 010
Create Date: 2025-12-11 16:05:00

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '011'
down_revision = '010'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 添加is_default字段
    op.add_column('bilibili_accounts', 
        sa.Column('is_default', sa.Boolean(), server_default='false', nullable=False, comment='是否为默认账号')
    )
    
    # 添加login_status字段
    op.add_column('bilibili_accounts',
        sa.Column('login_status', sa.String(20), server_default='pending', nullable=False, comment='登录状态')
    )
    
    # 创建复合索引
    op.create_index('idx_bilibili_account_default', 'bilibili_accounts', ['user_id', 'is_default'], unique=False)


def downgrade() -> None:
    # 删除索引
    op.drop_index('idx_bilibili_account_default', table_name='bilibili_accounts')
    
    # 删除字段
    op.drop_column('bilibili_accounts', 'login_status')
    op.drop_column('bilibili_accounts', 'is_default')
