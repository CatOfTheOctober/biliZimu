#!/usr/bin/env python3
"""测试多个视频的字幕下载功能。"""

import sys
import os
import logging
import re

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from bilibili_extractor.modules.bilibili_api import BilibiliAPI

def setup_logging():
    """设置日志。"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('multiple_videos_test.log', encoding='utf-8')
        ]
    )

def extract_bvid_from_url(url: str) -> str:
    """从 B 站 URL 中提取 BVID。"""
    bv_pattern = r'BV[a-zA-Z0-9]+'
    match = re.search(bv_pattern, url)
    
    if match:
        return match.group()
    else:
        raise ValueError(f"无法从 URL 中提取 BVID: {url}")

def test_video_subtitle(video_url: str, description: str = ""):
    """测试单个视频的字幕获取。"""
    print(f"\n{'='*60}")
    print(f"🎯 测试视频: {description}")
    print(f"📝 URL: {video_url}")
    
    try:
        # 提取 BVID
        bvid = extract_bvid_from_url(video_url)
        print(f"📋 BVID: {bvid}")
        
        # 创建 API 实例
        api = BilibiliAPI()
        
        # 获取视频信息
        video_info = api.get_video_info(bvid)
        aid = video_info['aid']
        cid = video_info['cid']
        title = video_info['title']
        
        print(f"📊 视频信息:")
        print(f"   - 标题: {title}")
        print(f"   - AID: {aid}")
        print(f"   - CID: {cid}")
        
        # 获取播放器信息（查看字幕列表）
        player_info = api.get_player_info(aid, cid)
        subtitles = player_info.get('subtitles', [])
        
        if subtitles:
            print(f"✅ 找到 {len(subtitles)} 个字幕:")
            for i, sub in enumerate(subtitles):
                lan = sub.get('lan', '')
                lan_doc = sub.get('lan_doc', '')
                subtitle_url = sub.get('subtitle_url', '')
                print(f"   [{i+1}] {lan} - {lan_doc}")
                print(f"       URL: {subtitle_url[:80]}{'...' if len(subtitle_url) > 80 else ''}")
            
            # 尝试下载第一个字幕
            first_subtitle = subtitles[0]
            subtitle_url = first_subtitle.get('subtitle_url')
            
            if subtitle_url:
                print(f"\n📥 尝试下载字幕: {first_subtitle.get('lan_doc')}")
                try:
                    subtitle_data = api.download_subtitle(subtitle_url)
                    if subtitle_data and subtitle_data.get('body'):
                        subtitle_list = subtitle_data['body']
                        print(f"✅ 字幕下载成功，共 {len(subtitle_list)} 条")
                        
                        # 显示前3条字幕
                        print(f"📖 字幕预览:")
                        for i, item in enumerate(subtitle_list[:3]):
                            content = item.get('content', '')
                            start_time = item.get('from', 0)
                            end_time = item.get('to', 0)
                            print(f"   [{i+1}] {start_time:.2f}s-{end_time:.2f}s: {content}")
                        
                        # 保存字幕文件
                        os.makedirs('output', exist_ok=True)
                        safe_title = re.sub(r'[<>:"/\\|?*]', '_', title)
                        filename = f"output/{safe_title}_{bvid}.srt"
                        
                        # 格式化为 SRT
                        srt_content = api._format_subtitles_to_srt(subtitle_list)
                        with open(filename, 'w', encoding='utf-8') as f:
                            f.write(srt_content)
                        
                        print(f"💾 字幕已保存到: {filename}")
                        return True
                    else:
                        print(f"❌ 字幕内容为空")
                        return False
                except Exception as e:
                    print(f"❌ 下载字幕失败: {e}")
                    return False
            else:
                print(f"❌ 字幕 URL 为空")
                return False
        else:
            print(f"❌ 该视频没有字幕")
            return False
            
    except Exception as e:
        print(f"❌ 处理失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主函数。"""
    print("🚀 多视频字幕下载测试")
    
    # 设置日志
    setup_logging()
    
    # 测试视频列表（选择一些可能有字幕的视频）
    test_videos = [
        {
            "url": "https://www.bilibili.com/video/BV1M8c7zSEBQ/",
            "description": "用户提供的视频"
        },
        {
            "url": "https://www.bilibili.com/video/BV1GJ411x7h7/",
            "description": "经典视频（可能有字幕）"
        },
        {
            "url": "https://www.bilibili.com/video/BV1uT4y1P7CX/",
            "description": "技术视频（可能有字幕）"
        }
    ]
    
    success_count = 0
    total_count = len(test_videos)
    
    for video in test_videos:
        try:
            if test_video_subtitle(video["url"], video["description"]):
                success_count += 1
        except Exception as e:
            print(f"❌ 测试视频失败: {e}")
    
    print(f"\n{'='*60}")
    print(f"📊 测试总结:")
    print(f"   - 总测试数: {total_count}")
    print(f"   - 成功数: {success_count}")
    print(f"   - 成功率: {success_count/total_count*100:.1f}%")
    
    print(f"\n✨ 测试完成！详细日志请查看 multiple_videos_test.log")

if __name__ == "__main__":
    main()