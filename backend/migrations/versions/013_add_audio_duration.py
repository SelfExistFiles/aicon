"""add audio_duration to sentences

Revision ID: 013_add_audio_duration
Revises: 012_add_account_id_to_publish_tasks
Create Date: 2025-12-12 10:20:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '013'
down_revision = '012'
branch_labels = None
depends_on = None


def upgrade():
    # 添加 audio_duration 字段到 sentences 表
    op.add_column('sentences', sa.Column('audio_duration', sa.Float(), nullable=True, comment='音频时长（秒）'))


def downgrade():
    # 移除 audio_duration 字段
    op.drop_column('sentences', 'audio_duration')
