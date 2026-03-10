#!/usr/bin/env python3
"""最终版本：下载指定视频的字幕文件。"""

import sys
import os
import re

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from bilibili_extractor.modules.bilibili_api import BilibiliAPI

def load_cookie():
    """加载 Cookie。"""
    cookie_path = 'tools/BBDown/BBDown.data'
    if os.path.exists(cookie_path):
        with open(cookie_path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    return None

def download_subtitle(video_url):
    """下载字幕。"""
    print(f"🎯 下载视频字幕: {video_url}")
    
    # 提取 BVID
    bv_pattern = r'BV[a-zA-Z0-9]+'
    match = re.search(bv_pattern, video_url)
    if not match:
        print("❌ 无法提取 BVID")
        return
    
    bvid = match.group()
    print(f"📝 BVID: {bvid}")
    
    # 加载 Cookie
    cookie = load_cookie()
    if cookie:
        print(f"✅ Cookie 加载成功")
    else:
        print("⚠️ 未找到 Cookie，可能影响 AI 字幕获取")
    
    # 创建 API 实例
    api = BilibiliAPI(cookie=cookie)
    
    try:
        # 获取视频信息
        video_info = api.get_video_info(bvid)
        title = video_info['title']
        cid = video_info['cid']
        
        print(f"📊 视频: {title}")
        
        # 获取字幕
        result = api.get_subtitle_with_ai_fallback(bvid, cid)
        
        if result.get('success'):
            metadata = result.get('metadata', {})
            subtitles = result.get('subtitles', [])
            subtitle_text = result.get('subtitle_text', '')
            
            print(f"✅ 字幕获取成功!")
            print(f"   - 语言: {metadata.get('lan_doc')}")
            print(f"   - 字幕条数: {len(subtitles)}")
            
            # 保存字幕文件（默认 TXT 格式）
            if subtitle_text:
                os.makedirs('output', exist_ok=True)
                safe_title = re.sub(r'[<>:"/\\|?*]', '_', title)
                
                # 保存 TXT 格式（默认）
                filename_txt = f"output/{safe_title}_{bvid}.txt"
                with open(filename_txt, 'w', encoding='utf-8') as f:
                    f.write(subtitle_text)
                
                print(f"💾 字幕已保存到: {filename_txt}")
                
                # 同时保存 SRT 格式（可选）
                if result.get('subtitle_text_srt'):
                    filename_srt = f"output/{safe_title}_{bvid}.srt"
                    with open(filename_srt, 'w', encoding='utf-8') as f:
                        f.write(result['subtitle_text_srt'])
                    print(f"📄 SRT 格式也已保存到: {filename_srt}")
                
                # 显示前3条字幕预览
                print(f"\n📖 字幕预览:")
                for i, subtitle in enumerate(subtitles[:3]):
                    content = subtitle.get('content', '')
                    start_time = subtitle.get('from', 0)
                    end_time = subtitle.get('to', 0)
                    print(f"   [{i+1}] {start_time:.1f}s-{end_time:.1f}s: {content}")
                
                return filename_txt
            else:
                print("❌ 字幕内容为空")
        else:
            print(f"❌ 字幕获取失败: {result.get('message')}")
        
    except Exception as e:
        print(f"❌ 处理失败: {e}")
        return None

def main():
    """主函数。"""
    video_url = "https://www.bilibili.com/video/BV1M8c7zSEBQ/?spm_id_from=333.1007.tianma.3-2-6.click&vd_source=cd3ecdc981801d2a54a308d648c1d491"
    
    filename = download_subtitle(video_url)
    
    if filename:
        print(f"\n🎉 字幕下载成功！文件保存在: {filename}")
    else:
        print(f"\n❌ 字幕下载失败")

if __name__ == "__main__":
    main()