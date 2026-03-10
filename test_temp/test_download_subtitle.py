#!/usr/bin/env python3
"""测试下载指定视频的字幕文件。"""

import sys
import os
import logging
import re

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from bilibili_extractor.modules.bilibili_api import BilibiliAPI
from bilibili_extractor.core.config import Config

def setup_logging():
    """设置日志。"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('subtitle_download.log', encoding='utf-8')
        ]
    )

def extract_bvid_from_url(url: str) -> str:
    """从 B 站 URL 中提取 BVID。"""
    # 匹配 BV 号的正则表达式
    bv_pattern = r'BV[a-zA-Z0-9]+'
    match = re.search(bv_pattern, url)
    
    if match:
        return match.group()
    else:
        raise ValueError(f"无法从 URL 中提取 BVID: {url}")

def download_subtitle_from_url(video_url: str):
    """从视频 URL 下载字幕。"""
    print(f"🎯 目标视频: {video_url}")
    
    # 提取 BVID
    try:
        bvid = extract_bvid_from_url(video_url)
        print(f"📝 提取到 BVID: {bvid}")
    except ValueError as e:
        print(f"❌ 错误: {e}")
        return
    
    # 创建 API 实例
    api = BilibiliAPI()
    
    try:
        # 步骤1：获取视频信息
        print("\n📊 步骤1：获取视频信息...")
        video_info = api.get_video_info(bvid)
        
        aid = video_info['aid']
        cid = video_info['cid']
        title = video_info['title']
        
        print(f"✅ 视频信息获取成功:")
        print(f"   - 标题: {title}")
        print(f"   - AID: {aid}")
        print(f"   - CID: {cid}")
        print(f"   - 分P数量: {video_info['page_count']}")
        
        # 步骤2：尝试获取字幕
        print(f"\n🎬 步骤2：获取字幕...")
        result = api.get_subtitle_with_ai_fallback(bvid, cid)
        
        if result.get('success'):
            metadata = result.get('metadata', {})
            subtitles = result.get('subtitles', [])
            subtitle_text = result.get('subtitle_text', '')
            
            print(f"✅ 字幕获取成功!")
            print(f"   - 语言: {metadata.get('lan')} - {metadata.get('lan_doc')}")
            print(f"   - 字幕条数: {len(subtitles)}")
            print(f"   - 字幕URL: {metadata.get('subtitle_url', '无')}")
            
            # 保存字幕文件
            if subtitle_text:
                # 创建输出目录
                os.makedirs('output', exist_ok=True)
                
                # 生成文件名（去除特殊字符）
                safe_title = re.sub(r'[<>:"/\\|?*]', '_', title)
                filename = f"output/{safe_title}_{bvid}.srt"
                
                # 保存 SRT 文件
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(subtitle_text)
                
                print(f"💾 字幕已保存到: {filename}")
                
                # 显示前几条字幕预览
                print(f"\n📖 字幕预览（前5条）:")
                for i, subtitle in enumerate(subtitles[:5]):
                    content = subtitle.get('content', '')
                    start_time = subtitle.get('from', 0)
                    end_time = subtitle.get('to', 0)
                    print(f"   [{i+1}] {start_time:.2f}s-{end_time:.2f}s: {content}")
                
                if len(subtitles) > 5:
                    print(f"   ... 还有 {len(subtitles) - 5} 条字幕")
            else:
                print("⚠️ 字幕内容为空")
        else:
            error_msg = result.get('message', '未知错误')
            print(f"❌ 字幕获取失败: {error_msg}")
            
            # 如果是因为没有字幕，尝试获取播放器信息查看详情
            print(f"\n🔍 尝试获取播放器详细信息...")
            try:
                player_info = api.get_player_info(aid, cid)
                subtitles = player_info.get('subtitles', [])
                
                if subtitles:
                    print(f"📋 找到 {len(subtitles)} 个字幕选项:")
                    for i, sub in enumerate(subtitles):
                        print(f"   [{i+1}] {sub.get('lan')} - {sub.get('lan_doc')} (URL: {sub.get('subtitle_url', '无')})")
                else:
                    print("📋 该视频确实没有字幕")
                    
            except Exception as e:
                print(f"❌ 获取播放器信息失败: {e}")
        
    except Exception as e:
        print(f"❌ 处理过程中出现错误: {e}")
        import traceback
        traceback.print_exc()

def main():
    """主函数。"""
    print("🚀 B站字幕下载测试")
    
    # 设置日志
    setup_logging()
    
    # 目标视频 URL
    video_url = "https://www.bilibili.com/video/BV1M8c7zSEBQ/?spm_id_from=333.1007.tianma.3-2-6.click&vd_source=cd3ecdc981801d2a54a308d648c1d491"
    
    # 下载字幕
    download_subtitle_from_url(video_url)
    
    print(f"\n✨ 测试完成！详细日志请查看 subtitle_download.log")

if __name__ == "__main__":
    main()