"""
字幕服务 - 处理字幕生成、时间轴和LLM纠错

负责:
- 使用Whisper生成字幕时间轴
- 使用LLM纠正字幕中的错别字
- 创建FFmpeg字幕滤镜
- 文本分割和格式化
"""

import re
from typing import Dict, List, Optional

from src.core.logging import get_logger
from src.models import APIKey
from src.services.faster_whisper_service import transcription_service
from src.services.provider.factory import ProviderFactory
from src.utils.ffmpeg_utils import get_audio_duration

logger = get_logger(__name__)


class SubtitleService:
    """字幕服务 - 处理所有字幕相关操作"""

    def generate_subtitle_timeline(self, audio_path: str) -> dict:
        """
        生成字幕时间轴

        Args:
            audio_path: 音频文件路径

        Returns:
            字幕数据，包含segments和duration
        """
        try:
            # 使用Whisper服务进行转录
            results, srt_content = transcription_service.transcribe(
                audio_path,
                output_format="json"
            )

            # 获取音频时长
            duration = get_audio_duration(audio_path) or 0

            return {
                "segments": results,
                "duration": duration
            }

        except Exception as e:
            logger.error(f"生成字幕时间轴失败: {e}")
            raise

    async def correct_subtitle_with_llm(
            self,
            subtitle_data: dict,
            original_text: str,
            api_key: APIKey,
            model: str = None
    ) -> dict:
        """
        使用LLM纠正字幕中的错别字

        Args:
            subtitle_data: Whisper生成的字幕数据（包含segments）
            original_text: 原始句子文本
            api_key: API密钥对象
            model: 模型名称（可选）

        Returns:
            纠正后的字幕数据
        """
        try:
            # 提取所有segment的文本
            segments = subtitle_data.get("segments", [])
            if not segments:
                logger.warning("字幕数据为空，跳过LLM纠错")
                return subtitle_data

            # 构建当前识别的文本
            recognized_text = " ".join([seg.get("text", "").strip() for seg in segments])

            # 如果识别文本为空，跳过
            if not recognized_text:
                logger.warning("识别文本为空，跳过LLM纠错")
                return subtitle_data

            # 创建LLM provider
            llm_provider = ProviderFactory.create(
                provider=api_key.provider,
                api_key=api_key.get_api_key(),
                max_concurrency=1,
                base_url=api_key.base_url if api_key.base_url else None
            )

            # 选择模型
            if not model:
                if api_key.provider == "deepseek":
                    model = "deepseek-chat"
                elif api_key.provider == "volcengine":
                    model = "doubao-pro"
                elif api_key.provider == "siliconflow":
                    model = "deepseek-ai/DeepSeek-V3.1-Terminus"
                else:
                    model = "gpt-4o-mini"

            # 构建提示词 - 简化版，直接要求返回纠正后的完整文本
            system_prompt = """你是一个专业的字幕纠错助手。你的任务是对比语音识别的字幕和原文，纠正字幕中的错别字。

规则：
1. 只纠正明显的错别字和识别错误
2. 参考原文内容，但要保持字幕的口语化特点
3. 不要改变句子的结构和语气
4. 如果字幕已经正确，保持原样
5. 返回JSON格式：{"corrected_text": "纠正后的完整文本"}"""

            user_prompt = f"""原文：
{original_text}

语音识别的字幕：
{recognized_text}

请纠正字幕中的错别字，返回纠正后的完整文本。"""

            # 调用LLM
            logger.info(f"[LLM纠错] 开始纠正字幕，模型: {model}")
            logger.debug(f"[LLM纠错] 原文: {original_text}")
            logger.debug(f"[LLM纠错] 识别文本: {recognized_text}")
            
            response = await llm_provider.completions(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"}
            )

            # 解析响应
            import json
            correction_result = json.loads(response.choices[0].message.content)
            corrected_full_text = correction_result.get("corrected_text", "").strip()
            
            if not corrected_full_text:
                logger.warning("[LLM纠错] LLM返回空文本，使用原始字幕")
                return subtitle_data
            
            logger.info(f"[LLM纠错] 纠正结果: {corrected_full_text}")

            # 将纠正后的文本应用到segments
            # 简单策略：将整个纠正后的文本作为第一个segment的文本，清空其他segments
            if len(segments) > 0:
                # 保留第一个segment的时间信息，更新文本
                segments[0]["text"] = corrected_full_text
                
                # 如果有词级时间轴，更新为单个词
                if "words" in segments[0]:
                    original_words = segments[0]["words"]
                    if original_words:
                        segments[0]["words"] = [{
                            "word": corrected_full_text,
                            "start": original_words[0].get("start", 0),
                            "end": original_words[-1].get("end", 0) if len(original_words) > 0 else 0
                        }]
                
                # 清空其他segments（如果有多个）
                # 保留它们是为了保持时间轴完整性，但文本置空
                for i in range(1, len(segments)):
                    segments[i]["text"] = ""
                    if "words" in segments[i]:
                        segments[i]["words"] = []

            logger.info(f"[LLM纠错] 纠正完成")
            return subtitle_data

        except Exception as e:
            logger.error(f"LLM纠正字幕失败: {e}", exc_info=True)
            # 失败时返回原始字幕
            logger.warning("LLM纠错失败，使用原始字幕")
            return subtitle_data

    def split_text_into_lines(self, text: str, max_chars: int = 18) -> list:
        """
        智能分割文本为双行字幕（漫画解说标准）

        Args:
            text: 要分割的文本
            max_chars: 每行最大字符数（推荐15-20字）

        Returns:
            分割后的行列表（最多2行，不含标点）
        """
        # 移除所有标点符号
        punctuation_pattern = r'[，。！？；、,\.!?;]'
        clean_text = re.sub(punctuation_pattern, '', text).strip()

        if not clean_text:
            return []

        # 如果文本很短，直接返回单行
        if len(clean_text) <= max_chars:
            return [clean_text]

        # 分成两行（漫画解说标准）
        # 尽量在中间位置分割
        mid_point = len(clean_text) // 2

        # 在中间点附近找最佳分割位置
        best_split = mid_point
        for i in range(max(mid_point - 5, 0), min(mid_point + 5, len(clean_text))):
            if i > 0 and i < len(clean_text):
                best_split = i
                break

        line1 = clean_text[:best_split].strip()
        line2 = clean_text[best_split:].strip()

        # 如果第二行太长，截断
        if len(line2) > max_chars:
            line2 = line2[:max_chars]

        # 如果第一行太长，调整
        if len(line1) > max_chars:
            line1 = line1[:max_chars]

        return [line1, line2] if line2 else [line1]

    def create_subtitle_filter(
            self,
            subtitle_data: dict,
            gen_setting: dict
    ) -> str:
        """
        创建漫画解说字幕滤镜（固定位置，专业样式）

        Args:
            subtitle_data: 字幕数据
            gen_setting: 生成设置

        Returns:
            FFmpeg drawtext滤镜字符串
        """
        try:
            subtitle_style = gen_setting.get("subtitle_style", {})
            font_size = subtitle_style.get("font_size", 70)  # 适中字号
            color = subtitle_style.get("color", "white")

            # 动态计算字幕位置
            resolution = gen_setting.get("resolution", "1440x1080")
            try:
                w_str, h_str = resolution.split('x')
                width = int(w_str)
                height = int(h_str)
            except:
                width = 1440
                height = 1080

            # 根据宽高比决定位置
            # 竖屏 (9:16) -> 下方30%处 (避开抖音/快手底部UI)
            # 横屏 (16:9, 4:3) -> 下方15%处
            if height > width:
                fixed_y_pos = int(height * 0.7)
            else:
                fixed_y_pos = int(height * 0.85)

            logger.info(f"视频分辨率: {width}x{height}, 字幕Y坐标: {fixed_y_pos}")

            # 标点符号正则（用于检测断句）
            split_pattern = r'[，。！？；、,\.!?;:\'"()\[\]{}<>]'
            # 仅用于移除显示的标点
            remove_pattern = r'[，。！？；、,\.!?;:\'"()\[\]{}<>]'

            filters = []
            segments = subtitle_data.get("segments", [])

            for segment in segments:
                words = segment.get("words", [])

                if words:
                    # 使用词级时间轴构建字幕行
                    current_line_words = []
                    current_line_len = 0

                    for w in words:
                        raw_word = w.get("word", "")
                        # 检查这个词是否包含标点符号（意味着小句结束）
                        has_punctuation = bool(re.search(split_pattern, raw_word))

                        # 移除标点用于显示和长度计算
                        clean_word = re.sub(remove_pattern, '', raw_word).strip()

                        if not clean_word:
                            # 即使是纯标点，如果它标志着句子结束，也可能触发换行
                            if has_punctuation and current_line_words:
                                # 输出当前行
                                line_text = "".join([x["text"] for x in current_line_words])
                                start_time = current_line_words[0]["start"]
                                end_time = current_line_words[-1]["end"]  # 使用上一个词的结束时间

                                text_escaped = line_text.replace("'", "'\\\\\\''").replace(":", "\\:")

                                filter_str = (
                                    f"drawtext="
                                    f"text='{text_escaped}':"
                                    f"fontsize={font_size}:"
                                    f"fontcolor={color}:"
                                    f"borderw=5:"
                                    f"bordercolor=black:"
                                    f"shadowcolor=black@0.7:"
                                    f"shadowx=4:"
                                    f"shadowy=4:"
                                    f"box=1:"
                                    f"boxcolor=black@0.65:"
                                    f"boxborderw=20:"
                                    f"x=(w-text_w)/2:"
                                    f"y={fixed_y_pos}:"
                                    f"enable='between(t,{start_time:.3f},{end_time:.3f})'"
                                )
                                filters.append(filter_str)

                                current_line_words = []
                                current_line_len = 0
                            continue

                        word_len = len(clean_word)

                        # 换行条件：
                        # 1. 加上当前词超过最大长度（18字）
                        # 2. 或者前一个词带有标点（已在上一轮循环处理，但这里作为双重保障）
                        # 注意：这里主要处理长度限制，标点断句在下面处理
                        if current_line_len + word_len > 18 and current_line_words:
                            # 输出当前行
                            line_text = "".join([x["text"] for x in current_line_words])
                            start_time = current_line_words[0]["start"]
                            end_time = current_line_words[-1]["end"]

                            text_escaped = line_text.replace("'", "'\\\\\\''").replace(":", "\\:")

                            filter_str = (
                                f"drawtext="
                                f"text='{text_escaped}':"
                                f"fontsize={font_size}:"
                                f"fontcolor={color}:"
                                f"borderw=5:"
                                f"bordercolor=black:"
                                f"shadowcolor=black@0.7:"
                                f"shadowx=4:"
                                f"shadowy=4:"
                                f"box=1:"
                                f"boxcolor=black@0.65:"
                                f"boxborderw=20:"
                                f"x=(w-text_w)/2:"
                                f"y={fixed_y_pos}:"
                                f"enable='between(t,{start_time:.3f},{end_time:.3f})'"
                            )
                            filters.append(filter_str)

                            current_line_words = []
                            current_line_len = 0

                        # 添加词到当前行
                        current_line_words.append({
                            "text": clean_word,
                            "start": w.get("start", 0),
                            "end": w.get("end", 0)
                        })
                        current_line_len += word_len

                        # 如果当前词带有标点，且当前行不为空，则强制换行（小句结束）
                        if has_punctuation and current_line_words:
                            line_text = "".join([x["text"] for x in current_line_words])
                            start_time = current_line_words[0]["start"]
                            end_time = current_line_words[-1]["end"]

                            text_escaped = line_text.replace("'", "'\\\\\\''").replace(":", "\\:")

                            filter_str = (
                                f"drawtext="
                                f"text='{text_escaped}':"
                                f"fontsize={font_size}:"
                                f"fontcolor={color}:"
                                f"borderw=5:"
                                f"bordercolor=black:"
                                f"shadowcolor=black@0.7:"
                                f"shadowx=4:"
                                f"shadowy=4:"
                                f"box=1:"
                                f"boxcolor=black@0.65:"
                                f"boxborderw=20:"
                                f"x=(w-text_w)/2:"
                                f"y={fixed_y_pos}:"
                                f"enable='between(t,{start_time:.3f},{end_time:.3f})'"
                            )
                            filters.append(filter_str)

                            current_line_words = []
                            current_line_len = 0

                    # 处理最后一行
                    if current_line_words:
                        line_text = "".join([x["text"] for x in current_line_words])
                        start_time = current_line_words[0]["start"]
                        end_time = current_line_words[-1]["end"]

                        text_escaped = line_text.replace("'", "'\\\\\\''").replace(":", "\\:")

                        filter_str = (
                            f"drawtext="
                            f"text='{text_escaped}':"
                            f"fontsize={font_size}:"
                            f"fontcolor={color}:"
                            f"borderw=5:"
                            f"bordercolor=black:"
                            f"shadowcolor=black@0.7:"
                            f"shadowx=4:"
                            f"shadowy=4:"
                            f"box=1:"
                            f"boxcolor=black@0.65:"
                            f"boxborderw=20:"
                            f"x=(w-text_w)/2:"
                            f"y={fixed_y_pos}:"
                            f"enable='between(t,{start_time:.3f},{end_time:.3f})'"
                        )
                        filters.append(filter_str)

                else:
                    # 没有词级时间轴，使用比例计算时间（回退方案）
                    text = segment.get("text", "").strip()
                    if not text:
                        continue

                    # 优先按标点分割
                    # 使用正则保留分隔符，以便知道在哪里分割的
                    parts = re.split(f'({split_pattern})', text)
                    lines = []
                    current_part = ""

                    for part in parts:
                        # 如果是标点
                        if re.match(split_pattern, part):
                            if current_part:
                                lines.append(current_part)
                                current_part = ""
                        else:
                            # 如果是文字
                            if len(current_part) + len(part) > 18:
                                if current_part:
                                    lines.append(current_part)
                                current_part = part
                            else:
                                current_part += part

                    if current_part:
                        lines.append(current_part)

                    # 移除每行中的标点
                    clean_lines = [re.sub(remove_pattern, '', line).strip() for line in lines if
                                   re.sub(remove_pattern, '', line).strip()]

                    if not clean_lines:
                        continue

                    segment_start = segment.get("start", 0)
                    segment_end = segment.get("end", 0)
                    total_duration = segment_end - segment_start
                    total_length = len("".join(clean_lines))

                    current_start = segment_start

                    for line_text in clean_lines:
                        # 按长度比例计算持续时间
                        line_len = len(line_text)
                        if total_length > 0:
                            line_duration = total_duration * (line_len / total_length)
                        else:
                            line_duration = total_duration / len(clean_lines)

                        line_end = current_start + line_duration

                        text_escaped = line_text.replace("'", "'\\\\\\''").replace(":", "\\:")

                        filter_str = (
                            f"drawtext="
                            f"text='{text_escaped}':"
                            f"fontsize={font_size}:"
                            f"fontcolor={color}:"
                            f"borderw=5:"
                            f"bordercolor=black:"
                            f"shadowcolor=black@0.7:"
                            f"shadowx=4:"
                            f"shadowy=4:"
                            f"box=1:"
                            f"boxcolor=black@0.65:"
                            f"boxborderw=20:"
                            f"x=(w-text_w)/2:"
                            f"y={fixed_y_pos}:"
                            f"enable='between(t,{current_start:.3f},{line_end:.3f})'"
                        )
                        filters.append(filter_str)

                        current_start = line_end

            if not filters:
                return ""

            return ",".join(filters)

        except Exception as e:
            logger.error(f"创建字幕滤镜失败: {e}", exc_info=True)
            return ""


# 创建全局实例
subtitle_service = SubtitleService()

__all__ = [
    "SubtitleService",
    "subtitle_service",
]
