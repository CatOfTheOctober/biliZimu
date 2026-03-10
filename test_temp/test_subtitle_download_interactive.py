"""
交互式测试：下载任意视频的 AI 字幕

这个脚本允许用户指定视频 URL，然后尝试下载其 AI 字幕。
"""

import sys
import logging
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from src.bilibili_extractor.modules.bilibili_api import BilibiliAPI
from src.bilibili_extractor.modules.url_validator import URLValidator

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_subtitle_download(video_url: str, cookie: str = None):
    """测试下载视频的 AI 字幕"""
    
    logger.info(f"开始测试，视频 URL: {video_url}")
    
    # 提取视频 ID
    try:
        video_id = URLValidator.extract_video_id(video_url)
        logger.info(f"✅ 提取的视频 ID: {video_id}")
    except Exception as e:
        logger.error(f"❌ 提取视频 ID 失败: {e}")
        return False
    
    # 创建 API 实例
    api = BilibiliAPI(cookie=cookie)
    if cookie:
        logger.info(f"✅ 使用 Cookie 进行请求 (长度: {len(cookie)} 字符)")
    else:
        logger.info("⚠️  使用无登录状态进行请求")
    
    # 获取视频信息
    try:
        logger.info(f"获取视频信息...")
        video_info = api.get_video_info(video_id)
        
        if not video_info or not video_info.get('aid'):
            logger.error(f"❌ 获取视频信息失败")
            return False
        
        logger.info(f"✅ 视频标题: {video_info.get('title')}")
        logger.info(f"   aid: {video_info.get('aid')}")
        logger.info(f"   cid: {video_info.get('cid')}")
        logger.info(f"   页数: {video_info.get('page_count')}")
        
        aid = video_info.get('aid')
        cid = video_info.get('cid')
        bvid = video_info.get('bvid')
        
        if not aid or not cid or not bvid:
            logger.error(f"❌ 视频信息不完整")
            return False
        
    except Exception as e:
        logger.error(f"❌ 获取视频信息异常: {e}")
        return False
    
    # 使用新的统一字幕获取函数
    try:
        logger.info(f"获取 AI 字幕...")
        result = api.get_subtitle_with_ai_fallback(aid, cid, bvid)
        
        if not result.get('success'):
            logger.warning(f"⚠️  获取字幕失败: {result.get('message')}")
            return False
        
        logger.info(f"✅ 成功获取字幕!")
        logger.info(f"   语言: {result['metadata'].get('lan')}")
        logger.info(f"   描述: {result['metadata'].get('lan_doc')}")
        logger.info(f"   数量: {len(result['subtitles'])} 条")
        
        # 显示前 5 条字幕
        logger.info("前 5 条字幕:")
        for i, subtitle in enumerate(result['subtitles'][:5], 1):
            content = subtitle.get('content', '')[:50]  # 只显示前 50 个字符
            logger.info(f"  [{i}] {subtitle.get('from'):.1f}s - {subtitle.get('to'):.1f}s: {content}")
        
        # 保存字幕到文件
        output_file = Path("output") / f"{bvid}_subtitle.srt"
        output_file.parent.mkdir(exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(result['subtitle_text'])
        
        logger.info(f"✅ 字幕已保存到: {output_file}")
        logger.info(f"   文件大小: {output_file.stat().st_size} 字节")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 获取字幕异常: {e}")
        return False


if __name__ == '__main__':
    logger.info("=" * 80)
    logger.info("交互式测试：下载视频的 AI 字幕")
    logger.info("=" * 80)
    
    # 从命令行参数获取视频 URL
    if len(sys.argv) > 1:
        video_url = sys.argv[1]
    else:
        # 默认测试 URL
        video_url = "https://www.bilibili.com/video/BV1M8c7zSEBQ/"
        logger.info(f"未指定视频 URL，使用默认: {video_url}")
    
    # 尝试从 BBDown 获取 Cookie
    cookie = None
    bbdown_cookie_path = Path("tools/BBDown/cookie.txt")
    if bbdown_cookie_path.exists():
        try:
            with open(bbdown_cookie_path, 'r', encoding='utf-8') as f:
                cookie = f.read().strip()
            logger.info(f"✅ 从 BBDown 加载 Cookie")
        except Exception as e:
            logger.warning(f"⚠️  无法读取 BBDown Cookie: {e}")
    
    success = test_subtitle_download(video_url, cookie)
    
    logger.info("=" * 80)
    if success:
        logger.info("✅ 测试成功！AI 字幕获取功能正常")
    else:
        logger.error("❌ 测试失败！请检查错误日志")
    logger.info("=" * 80)
    
    sys.exit(0 if success else 1)
