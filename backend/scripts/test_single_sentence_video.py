"""
测试单个句子视频生成

使用方法:
python scripts/test_single_sentence_video.py --sentence-id <句子ID>
python scripts/test_single_sentence_video.py --sentence-id <句子ID> --api-key-id <API密钥ID>  # 测试LLM纠错
python scripts/test_single_sentence_video.py --sentence-id <句子ID> --api-key-id <API密钥ID> --model deepseek-chat
"""

import asyncio
import sys
from pathlib import Path
import argparse

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.core.database import get_async_db
from src.models import Sentence
from src.services.video_composition_service import video_composition_service
from src.services.api_key import APIKeyService
from src.core.logging import get_logger
from sqlalchemy import select
from sqlalchemy.orm import selectinload
import tempfile
import shutil

logger = get_logger(__name__)


async def test_single_sentence(sentence_id: str, api_key_id: str = None, model: str = None):
    """
    测试单个句子的视频生成
    
    Args:
        sentence_id: 句子ID
        api_key_id: API密钥ID（可选，用于测试LLM纠错）
        model: 模型名称（可选）
    """
    temp_dir = None
    
    try:
        # 获取数据库会话
        async with get_async_db() as db_session:
            # 查询句子（包含关联数据以获取user_id）
            from src.models import Paragraph, Chapter, Project
            
            result = await db_session.execute(
                select(Sentence)
                .where(Sentence.id == sentence_id)
                .options(
                    selectinload(Sentence.paragraph)
                    .selectinload(Paragraph.chapter)
                    .selectinload(Chapter.project)
                )
            )
            sentence = result.scalar_one_or_none()
            
            if not sentence:
                logger.error(f"句子不存在: {sentence_id}")
                return
            
            logger.info(f"找到句子: {sentence.content[:50]}...")
            logger.info(f"完整内容: {sentence.content}")
            
            # 检查素材
            if not sentence.image_url:
                logger.error("句子缺少图片素材")
                return
            
            if not sentence.audio_url:
                logger.error("句子缺少音频素材")
                return
            
            logger.info(f"图片: {sentence.image_url}")
            logger.info(f"音频: {sentence.audio_url}")
            
            # 如果提供了API密钥ID，加载API密钥用于LLM纠错
            api_key = None
            if api_key_id:
                try:
                    user_id = str(sentence.paragraph.chapter.project.owner_id)
                    api_key_service = APIKeyService(db_session)
                    api_key = await api_key_service.get_api_key_by_id(api_key_id, user_id)
                    logger.info(f"✅ 已加载API密钥: {api_key.name} ({api_key.provider})")
                    logger.info(f"🤖 将使用LLM纠正字幕")
                    if model:
                        logger.info(f"📝 指定模型: {model}")
                except Exception as e:
                    logger.error(f"❌ 加载API密钥失败: {e}")
                    logger.warning("将不使用LLM纠错功能")
                    api_key = None
            else:
                logger.info("ℹ️  未提供API密钥，将不使用LLM纠错")
            
            # 创建临时目录
            temp_dir = Path(tempfile.mkdtemp(prefix="test_video_"))
            logger.info(f"临时目录: {temp_dir}")
            
            # 4:3横屏设置
            gen_setting = {
                "resolution": "1080x1920",  # 竖屏
                "fps": 30,
                "video_codec": "libx264",
                "audio_codec": "aac",
                "audio_bitrate": "192k",
                "zoom_speed": 0.0005,
                "subtitle_style": {
                    "font": "Arial",
                    "font_size": 70,  # 漫画解说标准
                    "color": "white",
                    "position": "bottom"
                }
            }
            
            # 生成视频
            logger.info("=" * 60)
            logger.info("开始生成视频...")
            logger.info("=" * 60)
            
            video_path = await video_composition_service.synthesize_sentence_video(
                sentence=sentence,
                temp_dir=temp_dir,
                index=0,
                gen_setting=gen_setting,
                api_key=api_key,
                model=model
            )
            
            # 输出结果
            output_dir = Path("./test_output")
            output_dir.mkdir(exist_ok=True)
            
            # 根据是否使用LLM纠错来命名输出文件
            suffix = "_with_llm" if api_key else "_no_llm"
            output_file = output_dir / f"sentence_{sentence_id[:8]}{suffix}.mp4"
            
            shutil.copy(video_path, output_file)
            
            logger.info("=" * 60)
            logger.info(f"✅ 视频生成成功!")
            logger.info(f"📹 输出文件: {output_file.absolute()}")
            logger.info(f"📊 文件大小: {output_file.stat().st_size / 1024 / 1024:.2f} MB")
            if api_key:
                logger.info(f"🤖 LLM纠错: 已启用 ({api_key.provider})")
            else:
                logger.info(f"🤖 LLM纠错: 未启用")
            logger.info("=" * 60)
            
            # 更新API密钥使用统计
            if api_key:
                try:
                    user_id = str(sentence.paragraph.chapter.project.owner_id)
                    api_key_service = APIKeyService(db_session)
                    await api_key_service.update_usage(api_key.id, user_id)
                    await db_session.commit()
                    logger.info(f"✅ 已更新API密钥使用统计")
                except Exception as e:
                    logger.warning(f"更新API密钥使用统计失败: {e}")
            
    except Exception as e:
        logger.error(f"❌ 测试失败: {e}", exc_info=True)
        
    finally:
        # 清理临时目录
        if temp_dir and temp_dir.exists():
            try:
                shutil.rmtree(temp_dir)
                logger.info(f"清理临时目录: {temp_dir}")
            except Exception as e:
                logger.error(f"清理临时目录失败: {e}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="测试单个句子视频生成",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 基础测试（不使用LLM纠错）
  python scripts/test_single_sentence_video.py --sentence-id abc123...
  
  # 测试LLM字幕纠错功能
  python scripts/test_single_sentence_video.py --sentence-id abc123... --api-key-id def456...
  
  # 指定LLM模型
  python scripts/test_single_sentence_video.py --sentence-id abc123... --api-key-id def456... --model deepseek-chat
        """
    )
    parser.add_argument(
        "--sentence-id",
        required=True,
        help="句子ID (UUID格式)"
    )
    parser.add_argument(
        "--api-key-id",
        required=False,
        help="API密钥ID (UUID格式，可选，用于测试LLM字幕纠错)"
    )
    parser.add_argument(
        "--model",
        required=False,
        help="LLM模型名称 (可选，如: deepseek-chat, gpt-4o-mini)"
    )
    
    args = parser.parse_args()
    
    # 运行测试
    asyncio.run(test_single_sentence(args.sentence_id, args.api_key_id, args.model))


if __name__ == "__main__":
    main()
