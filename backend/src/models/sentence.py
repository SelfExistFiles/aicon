"""
句子模型 - 最小视频生成单元
严格按照data-model.md规范实现
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Dict, List, TYPE_CHECKING

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import relationship

from .base import BaseModel

if TYPE_CHECKING:
    pass


class SentenceStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    GENERATED_PROMPTS = "generated_prompts"  # 提示词已生成
    GENERATED_IMAGE = "generated_image"  # 图片已生成
    GENERATED_AUDIO = "generated_audio"  # 音频已生成
    COMPLETED = "completed"
    FAILED = "failed"


class Sentence(BaseModel):
    """句子模型 - 最小视频生成单元"""
    __tablename__ = 'sentences'

    # 基础字段 (ID, created_at, updated_at 继承自 BaseModel)
    paragraph_id = Column(PostgreSQLUUID(as_uuid=True), ForeignKey('paragraphs.id'), nullable=False, index=True, comment="段落外键")
    content = Column(Text, nullable=False, comment="句子内容")

    # 结构信息
    order_index = Column(Integer, nullable=False, comment="在段落中的顺序")
    word_count = Column(Integer, default=0, comment="字数统计")
    character_count = Column(Integer, default=0, comment="字符数量")

    # 生成资源
    image_url = Column(String(500), nullable=True, comment="生成的图片URL")
    image_prompt = Column(Text, nullable=True, comment="图片生成提示词")
    image_style = Column(String(100), nullable=True, comment="图片风格")
    audio_url = Column(String(500), nullable=True, comment="生成的音频URL")

    # 处理状态
    status = Column(String(20), default=SentenceStatus.PENDING, index=True, comment="处理状态")

    # 关系定义
    paragraph = relationship("Paragraph", back_populates="sentences")

    # 索引定义
    __table_args__ = (
        Index('idx_sentence_paragraph', 'paragraph_id'),
        Index('idx_sentence_order', 'order_index'),
        Index('idx_sentence_status', 'status'),
    )

    def __repr__(self) -> str:
        return f"<Sentence(id={self.id}, order={self.order_index}, status={self.status})>"

    # ==================== 批量操作方法 ====================

    @classmethod
    async def batch_create(cls, db_session, sentences_data: List[Dict], paragraph_ids: List[str]) -> List[str]:
        """
        批量创建句子记录

        Args:
            db_session: 数据库会话
            sentences_data: 句子数据列表
            paragraph_ids: 对应的段落ID列表

        Returns:
            创建的句子ID列表
        """
        if not sentences_data:
            return []

        # 生成ID并添加到数据中
        sentence_ids = []
        for i, sentence_data in enumerate(sentences_data):
            sentence_id = uuid.uuid4()
            sentence_data['id'] = sentence_id
            sentence_data['paragraph_id'] = paragraph_ids[i]
            sentence_data.setdefault('status', SentenceStatus.PENDING.value)
            sentence_ids.append(sentence_id)

        # 批量插入
        await db_session.execute(
            cls.__table__.insert(),
            sentences_data
        )

        # 提交以确保获取ID
        await db_session.flush()

        # 返回插入的ID列表
        return sentence_ids


    @classmethod
    async def get_by_paragraph_id(cls, db_session, paragraph_id: str) -> List['Sentence']:
        """
        获取段落的所有句子

        Args:
            db_session: 数据库会话
            paragraph_id: 段落ID

        Returns:
            句子列表
        """
        result = await db_session.execute(
            select(cls).where(cls.paragraph_id == paragraph_id)
            .order_by(cls.order_index)
        )
        return result.scalars().all()

    @classmethod
    async def count_by_paragraph_id(cls, db_session, paragraph_id: str) -> int:
        """
        统计段落的句子数量

        Args:
            db_session: 数据库会话
            paragraph_id: 段落ID

        Returns:
            句子数量
        """
        from sqlalchemy import func
        result = await db_session.execute(
            select(func.count(cls.id)).where(cls.paragraph_id == paragraph_id)
        )
        return result.scalar()

    @classmethod
    async def get_by_project_id(cls, db_session, project_id: str) -> List['Sentence']:
        """
        获取项目的所有句子

        Args:
            db_session: 数据库会话
            project_id: 项目ID

        Returns:
            句子列表
        """
        # 通过嵌套子查询获取项目的所有句子
        from src.models.paragraph import Paragraph
        from src.models.chapter import Chapter

        result = await db_session.execute(
            select(cls)
            .where(cls.paragraph_id.in_(
                select(Paragraph.id).where(
                    Paragraph.chapter_id.in_(
                        select(Chapter.id).where(Chapter.project_id == project_id)
                    )
                )
            ))
            .order_by(cls.paragraph_id, cls.order_index)
        )
        return result.scalars().all()

    @classmethod
    async def get_pending_sentences(cls, db_session, limit: int = 100) -> List['Sentence']:
        """
        获取待处理的句子

        Args:
            db_session: 数据库会话
            limit: 限制数量

        Returns:
            待处理的句子列表
        """
        result = await db_session.execute(
            select(cls).where(cls.status == SentenceStatus.PENDING.value)
            .order_by(cls.created_at)
            .limit(limit)
        )
        return result.scalars().all()

    @classmethod
    async def delete_by_project_id(cls, db_session, project_id: str) -> int:
        """
        删除项目的所有句子

        Args:
            db_session: 数据库会话
            project_id: 项目ID

        Returns:
            删除的句子数量
        """
        # 通过嵌套子查询删除项目的所有句子
        from src.models.paragraph import Paragraph
        from src.models.chapter import Chapter

        # 先统计数量
        result = await db_session.execute(
            select(func.count(cls.id)).where(cls.paragraph_id.in_(
                select(Paragraph.id).where(
                    Paragraph.chapter_id.in_(
                        select(Chapter.id).where(Chapter.project_id == project_id)
                    )
                )
            ))
        )
        count = result.scalar()

        if count > 0:
            # 执行删除
            await db_session.execute(
                cls.__table__.delete().where(cls.paragraph_id.in_(
                    select(Paragraph.id).where(
                        Paragraph.chapter_id.in_(
                            select(Chapter.id).where(Chapter.project_id == project_id)
                        )
                    )
                ))
            )
            await db_session.flush()

        return count


__all__ = [
    "Sentence",
    "SentenceStatus",
]
