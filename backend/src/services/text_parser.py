"""
文本解析服务 - 智能章节识别和内容解析

提供服务：
- 多模式章节检测和识别
- 智能文本分段和分句
- 文本内容清理和标准化
- 结构化数据模型转换

设计原则：
- 支持多种章节标记格式
- 智能分割长章节
- 数据库安全的文本处理
- 可配置的解析参数

检测模式：
- 中文数字章节：第一章、第二章...
- 阿拉伯数字章节：1.、2.、Chapter 1...
- 英文章节：Chapter 1、Part 1、Section 1...
- 简单标记：1、2、3...
- 括号章节：（一）、[第一卷]...

严格按照data-model.md规范实现，专注于核心文本解析功能
"""
import asyncio
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

try:
    from src.core.exceptions import ValidationError
    from src.core.logging import get_logger
    from src.models.chapter import Chapter, ChapterStatus
    from src.models.paragraph import Paragraph, ParagraphAction
    from src.models.sentence import Sentence, SentenceStatus
except ImportError:
    # 用于独立测试的情况
    def get_logger(name):
        import logging
        return logging.getLogger(name)


    # 创建简单的ValidationError模拟
    class ValidationError(ValueError):
        pass


    # 创建简单的枚举模拟
    class ChapterStatus:
        PENDING = "pending"


    class ParagraphAction:
        KEEP = "keep"


    class SentenceStatus:
        PENDING = "pending"

logger = get_logger(__name__)


@dataclass
class ChapterDetection:
    """章节检测结果"""
    title: str
    content: str
    chapter_number: int
    start_position: int
    end_position: int
    detection_method: str  # regex, fallback
    confidence_score: float = 0.0


class ChapterDetector(ABC):
    """章节检测器抽象基类"""

    @abstractmethod
    def detect_chapters(self, text: str) -> List[ChapterDetection]:
        """检测章节"""
        pass


class RegexChapterDetector(ChapterDetector):
    """基于正则表达式的章节检测器"""

    def __init__(self):
        # 多种章节标记模式，按优先级排序
        self.patterns = [
            # 阿拉伯数字章节：第1章、第一章、Chapter 1
            {
                'pattern': r'^第[一二三四五六七八九十百千万0-9]+[章节回卷篇]',
                'name': 'chinese_numbered',
                'confidence': 0.9
            },
            # 简单数字章节：1.、2.、3.
            {
                'pattern': r'^(\d+)\.\s+.*',
                'name': 'simple_numbered_dot',
                'confidence': 0.85
            },
            # 数字章节：1. 第一章、1、Chapter 1
            {
                'pattern': r'^(\d+)\.?\s*(第?[一二三四五六七八九十百千万0-9]*[章节回卷篇]|Chapter\s*\d+|[一二三四五六七八九十百千万]+、)',
                'name': 'numbered',
                'confidence': 0.85
            },
            # 英文章节：Chapter 1, Part 1
            {
                'pattern': r'^(Chapter|Part|Section)\s+\d+',
                'name': 'english',
                'confidence': 0.8
            },
            # 简单数字标记：1、2、3、
            {
                'pattern': r'^(\d+)、',
                'name': 'simple_numbered',
                'confidence': 0.7
            },
            # 括号章节：（一）、[第一卷]
            {
                'pattern': r'^[【\(]\s*[第]?[一二三四五六七八九十百千万0-9]+\s*[章节回卷篇]\s*[】\)]',
                'name': 'bracketed',
                'confidence': 0.75
            }
        ]

        # 编译正则表达式
        self.compiled_patterns = []
        for pattern_info in self.patterns:
            compiled = re.compile(
                pattern_info['pattern'],
                re.MULTILINE | re.IGNORECASE
            )
            self.compiled_patterns.append({
                'compiled': compiled,
                'name': pattern_info['name'],
                'confidence': pattern_info['confidence']
            })

    def detect_chapters(self, text: str) -> List[ChapterDetection]:
        """使用正则表达式检测章节"""
        chapters = []
        lines = text.split('\n')

        chapter_number = 1
        current_position = 0
        chapter_start_positions = []

        # 查找所有可能的章节标题
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                current_position += len(lines[i]) + 1
                continue

            # 尝试匹配所有模式
            for pattern in self.compiled_patterns:
                match = pattern['compiled'].match(line)
                if match:
                    chapter_start_positions.append({
                        'line_index': i,
                        'title': line,
                        'position': current_position,
                        'confidence': pattern['confidence'],
                        'method': pattern['name']
                    })
                    break

            current_position += len(lines[i]) + 1

        # 如果没有检测到章节，创建单个章节
        if not chapter_start_positions:
            return [ChapterDetection(
                title="完整文档",
                content=text,
                chapter_number=1,
                start_position=0,
                end_position=len(text),
                detection_method="fallback",
                confidence_score=0.5
            )]

        # 构建章节内容
        for i, chapter_info in enumerate(chapter_start_positions):
            start_pos = chapter_info['position']

            # 确定章节结束位置
            if i < len(chapter_start_positions) - 1:
                end_pos = chapter_start_positions[i + 1]['position']
            else:
                end_pos = len(text)

            # 提取章节内容
            chapter_content = text[start_pos:end_pos].strip()

            # 移除标题行，只保留内容
            title_end = chapter_content.find('\n')
            if title_end > 0:
                content_only = chapter_content[title_end + 1:].strip()
            else:
                content_only = ""

            chapters.append(ChapterDetection(
                title=chapter_info['title'],
                content=content_only,
                chapter_number=chapter_number,
                start_position=start_pos,
                end_position=end_pos,
                detection_method=chapter_info['method'],
                confidence_score=chapter_info['confidence']
            ))

            chapter_number += 1

        return chapters


class TextParserService:
    """文本解析服务主类"""

    def __init__(self):
        self.detector = RegexChapterDetector()
        # 统计信息
        self.stats = {
            'total_documents_processed': 0,
            'total_chapters_detected': 0,
            'average_chapters_per_document': 0.0
        }

    def _split_long_chapter(self, text: str) -> List[ChapterDetection]:
        """分割过长的章节"""
        # 尝试按照语义边界分割
        split_patterns = [
            r'\n\s*\n',  # 双换行
            r'[。！？]\s*\n',  # 句号+换行
            r'[。！？]\s{2,}',  # 句号+多个空格
        ]

        chapters = []
        best_split_positions = []

        # 寻找最佳分割点
        for pattern in split_patterns:
            matches = list(re.finditer(pattern, text))
            if len(matches) >= 2:  # 至少找到2个分割点
                positions = [m.start() for m in matches]
                # 均匀选择分割点
                target_chapters = max(len(text) // 10000, 2)  # 每10k字符一个章节
                step = max(len(positions) // (target_chapters - 1), 1)
                selected_positions = [positions[i] for i in range(0, len(positions), step)]
                best_split_positions = selected_positions
                break

        if not best_split_positions:
            # 如果没有找到好的分割点，按固定长度分割
            chunk_size = 10000
            best_split_positions = list(range(chunk_size, len(text), chunk_size))

        # 创建章节
        prev_pos = 0
        chapter_num = 1

        for pos in best_split_positions:
            if pos > prev_pos + 1000:  # 确保章节有足够长度
                content = text[prev_pos:pos].strip()
                if content:
                    chapters.append(ChapterDetection(
                        title=f"第{chapter_num}部分",
                        content=content,
                        chapter_number=chapter_num,
                        start_position=prev_pos,
                        end_position=pos,
                        detection_method="auto_split",
                        confidence_score=0.6
                    ))
                    chapter_num += 1
                prev_pos = pos

        # 添加最后一部分
        if prev_pos < len(text):
            content = text[prev_pos:].strip()
            if content:
                chapters.append(ChapterDetection(
                    title=f"第{chapter_num}部分",
                    content=content,
                    chapter_number=chapter_num,
                    start_position=prev_pos,
                    end_position=len(text),
                    detection_method="auto_split",
                    confidence_score=0.6
                ))

        return chapters

    def _update_stats(self, chapter_count: int):
        """更新统计信息"""
        self.stats['total_documents_processed'] += 1
        self.stats['total_chapters_detected'] += chapter_count
        if self.stats['total_documents_processed'] > 0:
            self.stats['average_chapters_per_document'] = (
                    self.stats['total_chapters_detected'] /
                    self.stats['total_documents_processed']
            )

    async def parse_to_models(self, project_id: str, text: str, options: Optional[Dict[str, Any]] = None) -> Tuple[List[Dict], List[Dict], List[Dict]]:
        """
        解析文本并转换为数据库模型格式

        直接从章节开始解析，逐层构建段落和句子，避免重复解析。

        Args:
            project_id: 项目ID
            text: 待解析文本
            options: 解析选项

        Returns:
            (chapters_data, paragraphs_data, sentences_data): 三层数据结构
        """
        if not text or not text.strip():
            raise ValidationError("文本内容不能为空")

        options = options or {}
        min_chapter_length = options.get('min_chapter_length', 1000)

        logger.info(f"开始解析文档，文本长度: {len(text)} 字符")

        # 0. 标准化换行符
        cleaned_text = text.replace('\r\n', '\n').replace('\r', '\n')

        # 1. 检测章节
        chapters = self.detector.detect_chapters(cleaned_text)
        logger.info(f"检测到 {len(chapters)} 个章节")

        # 2. 如果章节太长，尝试进一步分割
        if len(chapters) == 1 and len(cleaned_text) > min_chapter_length * 2:
            logger.info("单个章节过长，尝试智能分割")
            chapters = self._split_long_chapter(cleaned_text)

        # 3. 导入文本分割工具
        from src.utils.text_utils import paragraph_splitter, sentence_splitter

        chapters_data = []
        paragraphs_data = []
        sentences_data = []

        # 4. 逐个章节处理，建立正确的层次关系
        for chapter_idx, chapter_detection in enumerate(chapters):
            # 清理章节标题和内容
            cleaned_title = chapter_detection.title.replace('\r\n', '\n').replace('\r', '\n').strip()
            cleaned_content = chapter_detection.content.replace('\r\n', '\n').replace('\r', '\n').strip()

            # 构建章节数据
            chapter_data = {
                'project_id': project_id,
                'title': cleaned_title,
                'content': cleaned_content,
                'chapter_number': chapter_detection.chapter_number,
                'word_count': len(cleaned_content),
                'paragraph_count': 0,  # 稍后更新
                'sentence_count': 0,  # 稍后更新
                'status': ChapterStatus.PENDING.value,
            }
            chapters_data.append(chapter_data)

            # 分割当前章节的段落
            chapter_paragraphs = paragraph_splitter.split_into_paragraphs(chapter_detection.content)

            chapter_sentence_count = 0
            # 记录当前章节在段落列表中的起始位置
            chapter_para_start_idx = len(paragraphs_data)

            # 5. 处理当前章节的段落
            for para_idx, paragraph_text in enumerate(chapter_paragraphs):
                # 清理段落文本
                cleaned_paragraph = paragraph_text.replace('\r\n', '\n').replace('\r', '\n').strip()

                # 构建段落数据
                paragraph_data = {
                    'chapter_id': None,  # 保存数据库后设置
                    'content': cleaned_paragraph,
                    'order_index': para_idx + 1,
                    'word_count': len(cleaned_paragraph),
                    'sentence_count': 0,  # 稍后更新
                    'action': ParagraphAction.KEEP.value,
                }
                paragraphs_data.append(paragraph_data)

                # 分割当前段落的句子
                paragraph_sentences = sentence_splitter.split_into_sentences(cleaned_paragraph)
                chapter_sentence_count += len(paragraph_sentences)
                paragraph_data['sentence_count'] = len(paragraph_sentences)

                # 记录当前段落在句子列表中的起始位置
                para_sent_start_idx = len(sentences_data)

                # 6. 处理当前段落的句子
                for sent_idx, sentence_text in enumerate(paragraph_sentences):
                    # 清理句子文本
                    cleaned_sentence = sentence_text.replace('\r\n', '\n').replace('\r', '\n').strip()

                    # 构建句子数据
                    sentence_data = {
                        'paragraph_id': None,  # 保存数据库后设置
                        'content': cleaned_sentence,
                        'order_index': sent_idx + 1,
                        'word_count': len(cleaned_sentence),
                        'character_count': len(cleaned_sentence),
                        'status': SentenceStatus.PENDING.value,
                    }
                    sentences_data.append(sentence_data)

            # 7. 更新章节数据的统计信息
            chapters_data[chapter_idx]['paragraph_count'] = len(chapter_paragraphs)
            chapters_data[chapter_idx]['sentence_count'] = chapter_sentence_count

        # 8. 更新统计信息
        self._update_stats(len(chapters))

        logger.info(f"解析完成: {len(chapters_data)} 章节, {len(paragraphs_data)} 段落, {len(sentences_data)} 句子")

        return chapters_data, paragraphs_data, sentences_data

    def get_detection_stats(self) -> Dict[str, Any]:
        """获取检测统计信息"""
        return self.stats.copy()


# 全局实例
text_parser_service = TextParserService()

__all__ = [
    'TextParserService',
    'ChapterDetection',
    'RegexChapterDetector',
    'text_parser_service'
]

if __name__ == "__main__":
    # 简单测试

    async def main():
        from src.utils.file_handlers import get_file_handler
        handler = get_file_handler("txt")
        file_content = await handler.read_file("./docs/庆余年.txt")

        # 测试 parse_to_models 方法
        chapters_data, paragraphs_data, sentences_data = await text_parser_service.parse_to_models(
            "test-project-id", file_content
        )

        print(f"解析完成: {len(chapters_data)} 章节, {len(paragraphs_data)} 段落, {len(sentences_data)} 句子")


    asyncio.run(main())
