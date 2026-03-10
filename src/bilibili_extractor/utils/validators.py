"""输入验证工具。"""

import re
import os
from pathlib import Path
from typing import Dict, Any, List


def validate_bvid(bvid: str) -> bool:
    """验证BVID格式。
    
    BVID格式：BV + 10位字符（数字和大小写字母）
    
    Args:
        bvid: 视频BVID
        
    Returns:
        如果格式有效返回True，否则返回False
    """
    if not bvid:
        return False
    
    # BVID格式：BV开头 + 10位字符
    pattern = r'^BV[a-zA-Z0-9]{10}$'
    return bool(re.match(pattern, bvid))


def validate_file_path(path: str, allowed_dir: str = None) -> bool:
    """验证文件路径安全性。
    
    防止路径遍历攻击（../, ../../等）。
    
    Args:
        path: 文件路径
        allowed_dir: 允许的目录（可选）
        
    Returns:
        如果路径安全返回True，否则返回False
    """
    if not path:
        return False
    
    try:
        # 转换为绝对路径
        abs_path = Path(path).resolve()
        
        # 检查路径遍历
        if '..' in path or path.startswith('/') or path.startswith('\\'):
            # 进一步验证解析后的路径
            if allowed_dir:
                allowed_abs = Path(allowed_dir).resolve()
                if not str(abs_path).startswith(str(allowed_abs)):
                    return False
        
        # 检查危险字符
        dangerous_chars = ['<', '>', '|', '\0']
        if any(char in path for char in dangerous_chars):
            return False
        
        return True
        
    except Exception:
        return False


def validate_api_response(response: Dict[str, Any], expected_fields: List[str]) -> bool:
    """验证API响应结构。
    
    Args:
        response: API响应字典
        expected_fields: 期望的字段列表
        
    Returns:
        如果响应包含所有期望字段返回True，否则返回False
    """
    if not isinstance(response, dict):
        return False
    
    for field in expected_fields:
        if field not in response:
            return False
    
    return True


def sanitize_input(text: str) -> str:
    """清理输入文本，防止注入攻击。
    
    Args:
        text: 输入文本
        
    Returns:
        清理后的文本
    """
    if not text:
        return ""
    
    # 移除控制字符
    sanitized = ''.join(char for char in text if ord(char) >= 32 or char in '\n\r\t')
    
    # 转义特殊字符
    sanitized = sanitized.replace('&', '&amp;')
    sanitized = sanitized.replace('<', '&lt;')
    sanitized = sanitized.replace('>', '&gt;')
    sanitized = sanitized.replace('"', '&quot;')
    sanitized = sanitized.replace("'", '&#x27;')
    
    return sanitized
