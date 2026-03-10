"""
Cookie 和 AI 字幕 API 诊断脚本

这个脚本用于诊断：
1. Cookie 是否有效
2. AI 字幕 API 是否能正常工作
3. 是否能获取 AI 字幕 URL
"""

import sys
import json
import logging
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from src.bilibili_extractor.modules.bilibili_api import BilibiliAPI
from src.bilibili_extractor.modules.url_validator import URLValidator

# 配置详细的日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def diagnose_cookie():
    """诊断 Cookie"""
    logger.info("=" * 80)
    logger.info("诊断 Cookie")
    logger.info("=" * 80)
    
    bbdown_cookie_path = Path("tools/BBDown/cookie.txt")
    
    if not bbdown_cookie_path.exists():
        logger.warning(f"❌ BBDown Cookie 文件不存在: {bbdown_cookie_path}")
        logger.info("请确保已运行 BBDown 登录，或手动将 Cookie 放在该位置")
        return None
    
    try:
        with open(bbdown_cookie_path, 'r', encoding='utf-8') as f:
            cookie = f.read().strip()
        
        if not cookie:
            logger.warning("❌ Cookie 文件为空")
            return None
        
        logger.info(f"✅ 读取 Cookie 成功 (长度: {len(cookie)} 字符)")
        logger.info(f"   前 50 字符: {cookie[:50]}...")
        
        # 检查关键的 Cookie 项
        has_sessdata = 'SESSDATA=' in cookie
        has_dede_user_id = 'DedeUserID=' in cookie
        has_bili_jct = 'bili_jct=' in cookie
        
        logger.info(f"   SESSDATA: {'✅' if has_sessdata else '❌'}")
        logger.info(f"   DedeUserID: {'✅' if has_dede_user_id else '❌'}")
        logger.info(f"   bili_jct: {'✅' if has_bili_jct else '❌'}")
        
        if has_sessdata and has_dede_user_id:
            logger.info("✅ Cookie 包含必要的关键项")
            return cookie
        else:
            logger.warning("⚠️  Cookie 缺少关键项，可能无法访问 AI 字幕 API")
            return cookie
        
    except Exception as e:
        logger.error(f"❌ 读取 Cookie 失败: {e}")
        return None


def test_ai_subtitle_api(cookie: str = None):
    """测试 AI 字幕 API"""
    logger.info("=" * 80)
    logger.info("测试 AI 字幕 API")
    logger.info("=" * 80)
    
    # 视频信息
    video_url = "https://www.bilibili.com/video/BV1M8c7zSEBQ/"
    
    try:
        video_id = URLValidator.extract_video_id(video_url)
        logger.info(f"✅ 提取视频 ID: {video_id}")
    except Exception as e:
        logger.error(f"❌ 提取视频 ID 失败: {e}")
        return False
    
    # 创建 API 实例
    api = BilibiliAPI(cookie=cookie)
    if cookie:
        logger.info(f"✅ 使用 Cookie 创建 API 实例")
    else:
        logger.warning(f"⚠️  未使用 Cookie 创建 API 实例")
    
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
        
        aid = video_info.get('aid')
        cid = video_info.get('cid')
        
    except Exception as e:
        logger.error(f"❌ 获取视频信息异常: {e}", exc_info=True)
        return False
    
    # 测试 AI 字幕 API
    try:
        logger.info("=" * 80)
        logger.info("调用 get_ai_subtitle_url() 获取 AI 字幕 URL")
        logger.info("=" * 80)
        
        ai_subtitle_url = api.get_ai_subtitle_url(aid, cid)
        
        if ai_subtitle_url:
            logger.info(f"✅ 获取 AI 字幕 URL 成功")
            logger.info(f"   URL: {ai_subtitle_url[:100]}...")
            return True
        else:
            logger.warning(f"⚠️  AI 字幕 URL 为空")
            logger.info("   可能原因:")
            logger.info("   1. 该视频没有 AI 字幕")
            logger.info("   2. Cookie 无效或过期")
            logger.info("   3. API 返回错误")
            return False
        
    except Exception as e:
        logger.error(f"❌ 获取 AI 字幕 URL 异常: {e}", exc_info=True)
        return False


def test_complete_subtitle_flow(cookie: str = None):
    """测试完整的字幕获取流程"""
    logger.info("=" * 80)
    logger.info("测试完整的字幕获取流程")
    logger.info("=" * 80)
    
    # 视频信息
    video_url = "https://www.bilibili.com/video/BV1M8c7zSEBQ/"
    
    try:
        video_id = URLValidator.extract_video_id(video_url)
    except Exception as e:
        logger.error(f"❌ 提取视频 ID 失败: {e}")
        return False
    
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
        bvid = video_info.get('bvid')
        
    except Exception as e:
        logger.error(f"❌ 获取视频信息异常: {e}", exc_info=True)
        return False
    
    # 使用新的统一字幕获取函数
    try:
        logger.info(f"调用 get_subtitle_with_ai_fallback() 获取字幕...")
        result = api.get_subtitle_with_ai_fallback(aid, cid, bvid)
        
        if not result.get('success'):
            logger.warning(f"⚠️  获取字幕失败: {result.get('message')}")
            return False
        
        logger.info(f"✅ 成功获取字幕!")
        logger.info(f"   语言: {result['metadata'].get('lan')}")
        logger.info(f"   描述: {result['metadata'].get('lan_doc')}")
        logger.info(f"   数量: {len(result['subtitles'])} 条")
        
        if result['subtitles']:
            logger.info("前 3 条字幕:")
            for i, subtitle in enumerate(result['subtitles'][:3], 1):
                content = subtitle.get('content', '')[:50]
                logger.info(f"  [{i}] {subtitle.get('from'):.1f}s - {subtitle.get('to'):.1f}s: {content}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 获取字幕异常: {e}", exc_info=True)
        return False


def main():
    """主诊断函数"""
    logger.info("=" * 80)
    logger.info("开始 Cookie 和 AI 字幕 API 诊断")
    logger.info("=" * 80)
    
    # 诊断 1: Cookie
    cookie = diagnose_cookie()
    
    # 诊断 2: AI 字幕 API
    result2 = test_ai_subtitle_api(cookie)
    
    # 诊断 3: 完整流程
    result3 = test_complete_subtitle_flow(cookie)
    
    logger.info("=" * 80)
    logger.info("诊断完成")
    logger.info("=" * 80)
    logger.info(f"Cookie: {'✅' if cookie else '❌'}")
    logger.info(f"AI 字幕 API: {'✅' if result2 else '❌'}")
    logger.info(f"完整流程: {'✅' if result3 else '❌'}")
    logger.info("=" * 80)
    
    if not cookie:
        logger.warning("\n⚠️  关键问题：Cookie 不可用")
        logger.info("解决方案：")
        logger.info("1. 运行 BBDown 进行登录")
        logger.info("2. 或手动将 Cookie 放在 tools/BBDown/cookie.txt")
        logger.info("3. Cookie 需要包含 SESSDATA 和 DedeUserID")


if __name__ == '__main__':
    main()
