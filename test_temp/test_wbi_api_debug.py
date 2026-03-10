"""
WBI API 诊断脚本

这个脚本用于诊断 WBI API 返回 0 字幕的原因。
添加详细的调试日志，记录：
1. WBI 签名的详细信息
2. 完整的 API 请求和响应
3. 与 JS 版本的对比
"""

import sys
import json
import logging
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from src.bilibili_extractor.modules.bilibili_api import BilibiliAPI
from src.bilibili_extractor.modules.wbi_sign import get_wbi_keys, encode_wbi
from src.bilibili_extractor.modules.url_validator import URLValidator

# 配置详细的日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def diagnose_wbi_signature():
    """诊断 WBI 签名"""
    logger.info("=" * 80)
    logger.info("诊断 WBI 签名")
    logger.info("=" * 80)
    
    # 获取 WBI 密钥
    wbi_keys = get_wbi_keys()
    if not wbi_keys:
        logger.error("❌ 无法获取 WBI 密钥")
        return False
    
    img_key, sub_key = wbi_keys
    logger.info(f"✅ 获取 WBI 密钥")
    logger.info(f"   img_key: {img_key} (长度: {len(img_key)})")
    logger.info(f"   sub_key: {sub_key} (长度: {len(sub_key)})")
    logger.info(f"   总长度: {len(img_key + sub_key)}")
    
    # 测试参数
    test_params = {'aid': 123456, 'cid': 789012}
    logger.info(f"测试参数: {test_params}")
    
    # 进行 WBI 签名
    try:
        signed_params = encode_wbi(test_params.copy(), img_key, sub_key)
        logger.info(f"✅ WBI 签名成功")
        logger.info(f"   签名后参数:")
        for k, v in signed_params.items():
            if k == 'w_rid':
                logger.info(f"     {k}: {v[:20]}... (长度: {len(v)})")
            else:
                logger.info(f"     {k}: {v}")
        return True
    except Exception as e:
        logger.error(f"❌ WBI 签名失败: {e}", exc_info=True)
        return False


def diagnose_wbi_api_request():
    """诊断 WBI API 请求"""
    logger.info("=" * 80)
    logger.info("诊断 WBI API 请求")
    logger.info("=" * 80)
    
    # 视频信息
    video_url = "https://www.bilibili.com/video/BV1M8c7zSEBQ/"
    
    try:
        video_id = URLValidator.extract_video_id(video_url)
        logger.info(f"✅ 提取视频 ID: {video_id}")
    except Exception as e:
        logger.error(f"❌ 提取视频 ID 失败: {e}")
        return False
    
    # 加载 Cookie
    cookie = None
    bbdown_cookie_path = Path("tools/BBDown/cookie.txt")
    if bbdown_cookie_path.exists():
        try:
            with open(bbdown_cookie_path, 'r', encoding='utf-8') as f:
                cookie = f.read().strip()
            logger.info(f"✅ 从 BBDown 加载 Cookie (长度: {len(cookie)} 字符)")
        except Exception as e:
            logger.warning(f"⚠️  无法读取 BBDown Cookie: {e}")
    else:
        logger.warning(f"⚠️  BBDown Cookie 文件不存在")
    
    # 创建 API 实例
    api = BilibiliAPI(cookie=cookie)
    logger.info("✅ 创建 BilibiliAPI 实例")
    
    # 获取视频信息
    try:
        logger.info("获取视频信息...")
        video_info = api.get_video_info(video_id)
        
        if not video_info or not video_info.get('aid'):
            logger.error(f"❌ 获取视频信息失败")
            return False
        
        logger.info(f"✅ 视频信息:")
        logger.info(f"   标题: {video_info.get('title')}")
        logger.info(f"   aid: {video_info.get('aid')}")
        logger.info(f"   cid: {video_info.get('cid')}")
        logger.info(f"   bvid: {video_info.get('bvid')}")
        
        aid = video_info.get('aid')
        cid = video_info.get('cid')
        
    except Exception as e:
        logger.error(f"❌ 获取视频信息异常: {e}", exc_info=True)
        return False
    
    # 诊断 WBI API 请求
    try:
        logger.info("=" * 80)
        logger.info("调用 get_player_info() 获取播放器信息")
        logger.info("=" * 80)
        
        player_info = api.get_player_info(aid, cid)
        
        logger.info(f"✅ 获取播放器信息成功")
        logger.info(f"   字幕数量: {len(player_info.get('subtitles', []))}")
        
        subtitles = player_info.get('subtitles', [])
        if subtitles:
            logger.info(f"   字幕列表:")
            for i, sub in enumerate(subtitles[:5], 1):
                logger.info(f"     [{i}] lan={sub.get('lan')}, lan_doc={sub.get('lan_doc')}, url={sub.get('subtitle_url', '')[:50]}...")
        else:
            logger.warning(f"⚠️  字幕列表为空！")
            
            # 输出完整的 API 响应用于诊断
            logger.info(f"完整的 subtitle_data:")
            subtitle_data = player_info.get('subtitle_data', {})
            logger.info(json.dumps(subtitle_data, indent=2, ensure_ascii=False)[:500])
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 获取播放器信息异常: {e}", exc_info=True)
        return False


def diagnose_ai_subtitle_api():
    """诊断 AI 字幕 API"""
    logger.info("=" * 80)
    logger.info("诊断 AI 字幕 API")
    logger.info("=" * 80)
    
    # 视频信息
    video_url = "https://www.bilibili.com/video/BV1M8c7zSEBQ/"
    
    try:
        video_id = URLValidator.extract_video_id(video_url)
    except Exception as e:
        logger.error(f"❌ 提取视频 ID 失败: {e}")
        return False
    
    # 加载 Cookie
    cookie = None
    bbdown_cookie_path = Path("tools/BBDown/cookie.txt")
    if bbdown_cookie_path.exists():
        try:
            with open(bbdown_cookie_path, 'r', encoding='utf-8') as f:
                cookie = f.read().strip()
        except Exception as e:
            logger.warning(f"⚠️  无法读取 BBDown Cookie: {e}")
    
    # 创建 API 实例
    api = BilibiliAPI(cookie=cookie)
    
    # 获取视频信息
    try:
        video_info = api.get_video_info(video_id)
        if not video_info or not video_info.get('aid'):
            logger.error(f"❌ 获取视频信息失败")
            return False
        
        aid = video_info.get('aid')
        cid = video_info.get('cid')
        
    except Exception as e:
        logger.error(f"❌ 获取视频信息异常: {e}", exc_info=True)
        return False
    
    # 调用 AI 字幕 API
    try:
        logger.info(f"调用 get_ai_subtitle_url() 获取 AI 字幕 URL")
        logger.info(f"   aid: {aid}, cid: {cid}")
        
        ai_subtitle_url = api.get_ai_subtitle_url(aid, cid)
        
        if ai_subtitle_url:
            logger.info(f"✅ 获取 AI 字幕 URL 成功")
            logger.info(f"   URL: {ai_subtitle_url[:100]}...")
            return True
        else:
            logger.warning(f"⚠️  AI 字幕 URL 为空")
            return False
        
    except Exception as e:
        logger.error(f"❌ 获取 AI 字幕 URL 异常: {e}", exc_info=True)
        return False


def main():
    """主诊断函数"""
    logger.info("=" * 80)
    logger.info("开始 WBI API 诊断")
    logger.info("=" * 80)
    
    # 诊断 1: WBI 签名
    result1 = diagnose_wbi_signature()
    
    # 诊断 2: WBI API 请求
    result2 = diagnose_wbi_api_request()
    
    # 诊断 3: AI 字幕 API
    result3 = diagnose_ai_subtitle_api()
    
    logger.info("=" * 80)
    logger.info("诊断完成")
    logger.info("=" * 80)
    logger.info(f"WBI 签名: {'✅' if result1 else '❌'}")
    logger.info(f"WBI API 请求: {'✅' if result2 else '❌'}")
    logger.info(f"AI 字幕 API: {'✅' if result3 else '❌'}")
    logger.info("=" * 80)


if __name__ == '__main__':
    main()
