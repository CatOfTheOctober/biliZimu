#!/usr/bin/env python3
"""
B站字幕下载工具 - 简化版
使用方法：直接运行此脚本，然后输入视频 URL
"""

import sys
import os
import re

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from bilibili_extractor.modules.bilibili_api import BilibiliAPI
from bilibili_extractor.core.config import Config
from bilibili_extractor.core.extractor import TextExtractor
from bilibili_extractor.modules.output_formatter import OutputFormatter

def load_cookie():
    """加载 Cookie。"""
    cookie_path = 'tools/BBDown/BBDown.data'
    if os.path.exists(cookie_path):
        with open(cookie_path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    return None

def extract_bvid(url_or_bvid):
    """从 URL 或直接输入中提取 BVID。"""
    # 如果直接输入 BVID
    if url_or_bvid.startswith('BV'):
        return url_or_bvid
    
    # 从 URL 中提取 BVID
    bv_pattern = r'BV[a-zA-Z0-9]+'
    match = re.search(bv_pattern, url_or_bvid)
    if match:
        return match.group()
    
    return None

def download_subtitle(video_input):
    """下载字幕。"""
    print(f"🎯 处理输入: {video_input}")
    
    # 提取 BVID
    bvid = extract_bvid(video_input)
    if not bvid:
        print("❌ 无法识别 BVID，请输入正确的 B 站视频 URL 或 BVID")
        return False
    
    print(f"📝 BVID: {bvid}")
    
    # 加载 Cookie
    cookie = load_cookie()
    if cookie:
        print(f"✅ Cookie 加载成功")
    else:
        print("⚠️ 未找到 Cookie，可能无法获取 AI 字幕")
        print("💡 建议：运行 tools/BBDown/BBDown.exe --login 获取 Cookie")
    
    # 创建 API 实例
    api = BilibiliAPI(cookie=cookie)
    
    try:
        # 获取视频信息
        print("📊 获取视频信息...")
        video_info = api.get_video_info(bvid)
        title = video_info['title']
        cid = video_info['cid']
        
        print(f"📺 视频标题: {title}")
        
        # 获取字幕
        print("🎬 获取字幕...")
        result = api.get_subtitle_with_ai_fallback(bvid, cid)
        
        if result.get('success'):
            metadata = result.get('metadata', {})
            subtitles = result.get('subtitles', [])
            subtitle_text = result.get('subtitle_text', '')
            
            print(f"✅ 字幕获取成功!")
            print(f"   - 语言: {metadata.get('lan_doc', '未知')}")
            print(f"   - 字幕条数: {len(subtitles)}")
            
            # 保存字幕文件
            if subtitle_text:
                os.makedirs('output', exist_ok=True)
                safe_title = re.sub(r'[<>:"/\\|?*]', '_', title)
                
                # 保存 TXT 格式（默认）
                filename_txt = f"output/{safe_title}_{bvid}.txt"
                with open(filename_txt, 'w', encoding='utf-8') as f:
                    f.write(subtitle_text)
                
                print(f"💾 TXT 字幕已保存: {filename_txt}")
                
                # 同时保存 SRT 格式
                if result.get('subtitle_text_srt'):
                    filename_srt = f"output/{safe_title}_{bvid}.srt"
                    with open(filename_srt, 'w', encoding='utf-8') as f:
                        f.write(result['subtitle_text_srt'])
                    print(f"📄 SRT 字幕已保存: {filename_srt}")
                
                # 显示字幕预览
                print(f"\n📖 字幕预览（前5条）:")
                for i, subtitle in enumerate(subtitles[:5]):
                    content = subtitle.get('content', '')
                    print(f"   {content}")
                
                if len(subtitles) > 5:
                    print(f"   ... 还有 {len(subtitles) - 5} 条字幕")
                
                return True
            else:
                print("❌ 字幕内容为空")
                choice = input("\n💡 是否继续下载视频并用模型识别字幕？(y/n): ").strip().lower()
                if choice in ['y', 'yes', '是']:
                    print("\n🚀 开始视频下载与模型识别流程...")
                    try:
                        url = f"https://www.bilibili.com/video/{bvid}"
                        config = Config()
                        extractor = TextExtractor(config)
                        asr_result = extractor.extract(url)
                        
                        if asr_result and asr_result.segments:
                            os.makedirs('output', exist_ok=True)
                            local_title = title if 'title' in locals() else bvid
                            safe_title = re.sub(r'[<>:"/\\|?*]', '_', local_title)
                            
                            filename_txt = f"output/{safe_title}_{bvid}_asr.txt"
                            filename_srt = f"output/{safe_title}_{bvid}_asr.srt"
                            
                            with open(filename_txt, 'w', encoding='utf-8') as f:
                                f.write(OutputFormatter.to_txt(asr_result.segments))
                                
                            with open(filename_srt, 'w', encoding='utf-8') as f:
                                f.write(OutputFormatter.to_srt(asr_result.segments))
                                
                            print(f"\n🎉 哇哦！模型发威啦，字幕识别大功告成！")
                            print(f"💾 TXT 格式字幕已安稳存入: {filename_txt}")
                            print(f"📄 SRT 格式字幕也已存好啦: {filename_srt}")
                            return True
                        else:
                            print("💔 诶呀，模型跑完怎么是空的？啥也没提取出来噢")
                            return False
                    except Exception as e:
                        print(f"\n💥 模型提取不幸夭折，报错如下: {e}")
                        return False
                return False
        else:
            error_msg = result.get('message', '未知错误')
            print(f"❌ 字幕获取失败: {error_msg}")
            choice = input("\n💡 是否继续下载视频并用模型识别字幕？(y/n): ").strip().lower()
            if choice in ['y', 'yes', '是']:
                print("\n🚀 开始视频下载与模型识别流程...")
                try:
                    url = f"https://www.bilibili.com/video/{bvid}"
                    config = Config()
                    extractor = TextExtractor(config)
                    asr_result = extractor.extract(url)
                    
                    if asr_result and asr_result.segments:
                        os.makedirs('output', exist_ok=True)
                        local_title = title if 'title' in locals() else bvid
                        safe_title = re.sub(r'[<>:"/\\|?*]', '_', local_title)
                        
                        filename_txt = f"output/{safe_title}_{bvid}_asr.txt"
                        filename_srt = f"output/{safe_title}_{bvid}_asr.srt"
                        
                        with open(filename_txt, 'w', encoding='utf-8') as f:
                            f.write(OutputFormatter.to_txt(asr_result.segments))
                            
                        with open(filename_srt, 'w', encoding='utf-8') as f:
                            f.write(OutputFormatter.to_srt(asr_result.segments))
                            
                        print(f"\n🎉 哇哦！模型发威啦，字幕识别大功告成！")
                        print(f"💾 TXT 格式字幕已安稳存入: {filename_txt}")
                        print(f"📄 SRT 格式字幕也已存好啦: {filename_srt}")
                        return True
                    else:
                        print("💔 诶呀，模型跑完怎么是空的？啥也没提取出来噢")
                        return False
                except Exception as e:
                    print(f"\n💥 模型提取不幸夭折，报错如下: {e}")
                    return False
            return False
        
    except Exception as e:
        print(f"❌ 处理失败: {e}")
        return False

def main():
    """主函数。"""
    print("🚀 B站字幕下载工具")
    print("=" * 50)
    
    # 检查 Cookie 状态
    cookie = load_cookie()
    if not cookie:
        print("⚠️  重要提示：")
        print("   为了获取 AI 字幕，建议先获取 Cookie：")
        print("   1. 进入 tools/BBDown/ 目录")
        print("   2. 运行 BBDown.exe --login")
        print("   3. 按提示完成登录")
        print()
    
    while True:
        print("\n请输入以下任一格式：")
        print("1. 完整 URL: https://www.bilibili.com/video/BV1M8c7zSEBQ/")
        print("2. 短链接: https://b23.tv/xxxxx")
        print("3. 直接 BVID: BV1M8c7zSEBQ")
        print("4. 输入 'q' 或 'quit' 退出")
        
        user_input = input("\n🎯 请输入: ").strip()
        
        if user_input.lower() in ['q', 'quit', '退出']:
            print("👋 再见！")
            break
        
        if not user_input:
            print("❌ 输入不能为空")
            continue
        
        print("\n" + "=" * 50)
        success = download_subtitle(user_input)
        
        if success:
            print("\n🎉 下载完成！文件保存在 output/ 目录")
        else:
            print("\n😞 下载失败，请检查输入或网络连接")
        
        print("=" * 50)
        
        # 询问是否继续
        continue_choice = input("\n是否继续下载其他视频？(y/n): ").strip().lower()
        if continue_choice not in ['y', 'yes', '是', '继续']:
            print("👋 再见！")
            break

if __name__ == "__main__":
    main()