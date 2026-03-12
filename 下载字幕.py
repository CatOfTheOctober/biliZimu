#!/usr/bin/env python3
"""
B站字幕下载工具 - 简化版
使用方法：直接运行此脚本，然后输入视频 URL
"""

import sys
import os
import re
import json
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from bilibili_extractor.core.config import Config
from bilibili_extractor.core.extractor import TextExtractor
from bilibili_extractor.modules.output_formatter import OutputFormatter
from bilibili_extractor.core.exceptions import SubtitleNotFoundError

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
    
    try:
        print("📊 创建标准化采集产物...")
        url = f"https://www.bilibili.com/video/{bvid}"
        config = Config()
        extractor = TextExtractor(config)
        output_root = config.resolved_output_dir

        try:
            result = extractor.extract(url, artifact_dir=output_root)
        except SubtitleNotFoundError:
            print("❌ 未找到可用字幕")
            choice = input("\n💡 是否继续下载视频并用模型识别字幕？(y/n): ").strip().lower()
            if choice in ['y', 'yes', '是']:
                print("\n🚀 开始视频下载与模型识别流程...")
                try:
                    result = extractor.extract(url, force_asr=True, artifact_dir=output_root)
                except Exception as e:
                    print(f"\n💥 模型提取不幸夭折，报错如下: {e}")
                    return False
            else:
                return False

        if not result or not result.segments:
            print("💔 本次处理没有得到可用文本片段")
            return False

        title = result.video_info.title or bvid
        bundle_dir = Path(result.metadata.get("artifact_bundle_dir", output_root))
        derived_dir = bundle_dir / "derived"
        filename_txt = derived_dir / "selected_track.txt"
        filename_srt = derived_dir / "selected_track.srt"

        if not filename_txt.exists():
            filename_txt.write_text(OutputFormatter.to_txt(result.segments), encoding='utf-8')
        if not filename_srt.exists():
            filename_srt.write_text(OutputFormatter.to_srt(result.segments), encoding='utf-8')

        track_source = "asr"
        if result.method != "asr":
            track_source = "platform_ai_subtitle" if result.metadata.get("subtitle_kind") == "ai" else "platform_subtitle"
        manifest_path = bundle_dir / "manifest" / "AssetManifest.json"
        manifest_status = ""
        if manifest_path.exists():
            try:
                manifest_status = json.loads(manifest_path.read_text(encoding="utf-8")).get("status", "")
            except Exception:
                manifest_status = ""

        print(f"📺 视频标题: {title}")
        print(f"🧭 采用轨道: {track_source}")
        print(f"✅ 标准化字幕包已生成")
        print(f"📦 Bundle 目录: {bundle_dir}")
        print(f"🧾 TranscriptBundle: {derived_dir / 'TranscriptBundle.json'}")
        print(f"🗂️ AssetManifest: {manifest_path}")
        if manifest_status:
            print(f"📌 Manifest 状态: {manifest_status}")
        print(f"💾 TXT 字幕已保存: {filename_txt}")
        print(f"📄 SRT 字幕已保存: {filename_srt}")

        print(f"\n📖 字幕预览（前5条）:")
        for segment in result.segments[:5]:
            print(f"   {segment.text}")

        if len(result.segments) > 5:
            print(f"   ... 还有 {len(result.segments) - 5} 条字幕")
        return True
        
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
