"""B站 WBI 签名模块。

实现 WBI 签名算法，用于对 API 请求进行签名。
参考：https://xtcqinghe.github.io/bac/docs/misc/sign/wbi.html
"""

import hashlib
import time
import urllib.parse
from functools import reduce
from typing import Dict, Any, Optional, Tuple
import logging
import requests

logger = logging.getLogger(__name__)

# WBI 签名重排映射表
MIXIN_KEY_ENC_TAB = [
    46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35, 27, 43, 5, 49,
    33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13, 37, 48, 7, 16, 24, 55, 40,
    61, 26, 17, 0, 1, 60, 51, 30, 4, 22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11,
    36, 20, 34, 44, 52
]


def get_mixin_key(orig: str) -> str:
    """对 imgKey 和 subKey 进行字符顺序打乱编码。
    
    Args:
        orig: img_key + sub_key 的拼接字符串
        
    Returns:
        生成的 mixin_key（前 32 位）
    """
    return reduce(lambda s, i: s + orig[i], MIXIN_KEY_ENC_TAB, '')[:32]


def encode_wbi(params: Dict[str, Any], img_key: str, sub_key: str) -> Dict[str, Any]:
    """为请求参数进行 WBI 签名。
    
    参考：https://xtcqinghe.github.io/bac/docs/misc/sign/wbi.html
    
    Args:
        params: 原始请求参数
        img_key: 图片密钥
        sub_key: 子密钥
        
    Returns:
        添加了 w_rid 和 wts 的参数字典
    """
    # 生成 mixin_key
    mixin_key = get_mixin_key(img_key + sub_key)
    
    # 添加时间戳
    curr_time = round(time.time())
    params['wts'] = curr_time
    
    # 按照 key 重排参数
    params = dict(sorted(params.items()))
    
    # 过滤 value 中的 "!'()*" 字符
    params = {
        k: ''.join(filter(lambda chr: chr not in "!'()*", str(v)))
        for k, v in params.items()
    }
    
    # 序列化参数
    query = urllib.parse.urlencode(params)
    
    # 计算 w_rid
    wbi_sign = hashlib.md5((query + mixin_key).encode()).hexdigest()
    
    # 添加签名到参数
    params['w_rid'] = wbi_sign
    
    return params


def get_wbi_keys() -> Optional[Tuple[str, str]]:
    """获取最新的 img_key 和 sub_key。
    
    Returns:
        (img_key, sub_key) 元组，失败返回 None
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3',
            'Referer': 'https://www.bilibili.com/'
        }
        
        resp = requests.get('https://api.bilibili.com/x/web-interface/nav', headers=headers, timeout=10)
        resp.raise_for_status()
        
        json_content = resp.json()
        
        # 检查响应
        if json_content.get('code') not in [0, -101]:
            logger.warning(f"Failed to get WBI keys: {json_content.get('message')}")
            return None
        
        img_url: str = json_content['data']['wbi_img']['img_url']
        sub_url: str = json_content['data']['wbi_img']['sub_url']
        
        # 提取文件名（去掉路径和扩展名）
        img_key = img_url.rsplit('/', 1)[1].split('.')[0]
        sub_key = sub_url.rsplit('/', 1)[1].split('.')[0]
        
        logger.debug(f"Got WBI keys: img_key={img_key}, sub_key={sub_key}")
        
        return img_key, sub_key
        
    except Exception as e:
        logger.error(f"Failed to get WBI keys: {e}")
        return None
