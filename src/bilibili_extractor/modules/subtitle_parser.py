"""字幕解析模块。"""

import logging
from typing import Dict, Any, List
from ..core.models import TextSegment


class SubtitleParser:
    """字幕解析器。
    
    负责：
    1. 检测字幕格式（AI字幕 vs 普通字幕）
    2. 解析不同格式的字幕数据
    3. 转换为统一的TextSegment格式
    """
    
    @staticmethod
    def is_ai_subtitle_format(data: Dict[str, Any]) -> bool:
        """检测是否为AI字幕格式。
        
        AI字幕格式特征：
        - 包含body数组
        - body数组元素包含from、to、content字段
        
        Args:
            data: 字幕JSON数据
            
        Returns:
            如果是AI字幕格式返回True，否则返回False
        """
        if not isinstance(data, dict):
            return False
        
        body = data.get('body')
        if not isinstance(body, list) or len(body) == 0:
            return False
        
        # 检查第一个元素是否包含AI字幕特征字段
        first_item = body[0]
        return all(key in first_item for key in ['from', 'to', 'content'])
    
    @staticmethod
    def parse_subtitle(data: Dict[str, Any]) -> List[TextSegment]:
        """统一的字幕解析入口。
        
        自动检测字幕格式并调用相应的解析方法。
        
        Args:
            data: 字幕JSON数据
            
        Returns:
            TextSegment列表
        """
        logger = logging.getLogger(__name__)
        
        if SubtitleParser.is_ai_subtitle_format(data):
            logger.debug("Detected AI subtitle format")
            return SubtitleParser.parse_ai_subtitle(data)
        else:
            logger.debug("Detected regular subtitle format")
            return SubtitleParser.parse_regular_subtitle(data)
    
    @staticmethod
    def parse_ai_subtitle(data: Dict[str, Any]) -> List[TextSegment]:
        """解析AI字幕格式。
        
        AI字幕格式：
        {
            "body": [
                {"from": 0.0, "to": 2.5, "content": "文本内容"},
                ...
            ]
        }
        
        Args:
            data: AI字幕JSON数据
            
        Returns:
            TextSegment列表（已排序和验证）
        """
        logger = logging.getLogger(__name__)
        segments = []
        
        body = data.get('body', [])
        for item in body:
            try:
                # 提取字段并转换为float
                start_time = float(item['from'])
                end_time = float(item['to'])
                text = item['content'].strip()
                
                # 跳过空文本
                if not text:
                    continue
                
                # 验证时间戳
                if start_time >= end_time:
                    logger.warning(f"Invalid timestamp: start_time ({start_time}) >= end_time ({end_time})")
                    continue
                
                # 创建TextSegment
                segment = TextSegment(
                    start_time=start_time,
                    end_time=end_time,
                    text=text,
                    confidence=1.0,
                    source='subtitle'
                )
                segments.append(segment)
                
            except (KeyError, ValueError, TypeError) as e:
                logger.warning(f"Failed to parse AI subtitle item: {e}")
                continue
        
        # 按start_time升序排序
        segments.sort(key=lambda s: s.start_time)
        
        # 验证相邻片段无重叠
        for i in range(len(segments) - 1):
            if segments[i].end_time > segments[i + 1].start_time:
                logger.warning(
                    f"Overlapping segments detected: "
                    f"[{segments[i].start_time}-{segments[i].end_time}] and "
                    f"[{segments[i + 1].start_time}-{segments[i + 1].end_time}]"
                )
        
        logger.debug(f"Parsed {len(segments)} AI subtitle segments")
        return segments
    
    @staticmethod
    def parse_regular_subtitle(data: Dict[str, Any]) -> List[TextSegment]:
        """解析普通字幕格式。
        
        普通字幕格式：
        {
            "body": [
                {"from": 0.0, "to": 2.5, "content": "文本内容"},
                ...
            ]
        }
        
        注意：普通字幕和AI字幕的JSON格式实际上是相同的，
        区别在于来源（播放器API vs AI字幕API）。
        
        Args:
            data: 普通字幕JSON数据
            
        Returns:
            TextSegment列表（已排序和验证）
        """
        logger = logging.getLogger(__name__)
        segments = []
        
        body = data.get('body', [])
        for item in body:
            try:
                # 提取字段并转换为float
                start_time = float(item['from'])
                end_time = float(item['to'])
                text = item['content'].strip()
                
                # 跳过空文本
                if not text:
                    continue
                
                # 验证时间戳
                if start_time >= end_time:
                    logger.warning(f"Invalid timestamp: start_time ({start_time}) >= end_time ({end_time})")
                    continue
                
                # 创建TextSegment
                segment = TextSegment(
                    start_time=start_time,
                    end_time=end_time,
                    text=text,
                    confidence=1.0,
                    source='subtitle'
                )
                segments.append(segment)
                
            except (KeyError, ValueError, TypeError) as e:
                logger.warning(f"Failed to parse regular subtitle item: {e}")
                continue
        
        # 按start_time升序排序
        segments.sort(key=lambda s: s.start_time)
        
        # 验证相邻片段无重叠
        for i in range(len(segments) - 1):
            if segments[i].end_time > segments[i + 1].start_time:
                logger.warning(
                    f"Overlapping segments detected: "
                    f"[{segments[i].start_time}-{segments[i].end_time}] and "
                    f"[{segments[i + 1].start_time}-{segments[i + 1].end_time}]"
                )
        
        logger.debug(f"Parsed {len(segments)} regular subtitle segments")
        return segments
