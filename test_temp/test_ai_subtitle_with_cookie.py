#!/usr/bin/env python3
"""测试带 Cookie 的 AI 字幕获取功能。"""

import sys
import os
import logging

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from bilibili_extractor.modules.bilibili_api import BilibiliAPI

def setup_logging():
    """设置日志。"""
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('ai_subtitle_test.log', encoding='utf-8')
        ]
    )

def load_cookie_from_file():
    """从文件加载 Cookie。"""
    cookie_paths = [
        'tools/BBDown/BBDown.data',  # BBDown 的实际 Cookie 文件
        'tools/BBDown/cookie.txt',
        'cookie.txt',
        'config/cookie.txt'
    ]
    
    for path in cookie_paths:
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if content:
                        print(f"✅ 从 {path} 加载 Cookie 成功")
                        print(f"📄 Cookie 内容长度: {len(content)} 字符")
                        # 显示 Cookie 的前50个字符（用于调试）
                        preview = content[:50] + "..." if len(content) > 50 else content
                        print(f"🔍 Cookie 预览: {preview}")
                        return content
            except Exception as e:
                print(f"⚠️ 读取 {path} 失败: {e}")
        else:
            print(f"📁 文件不存在: {path}")
    
    print("❌ 未找到 Cookie 文件")
    return None

def test_ai_subtitle():
    """测试 AI 字幕获取。"""
    print("🚀 AI 字幕获取测试")
    
    # 目标视频信息
    video_url = "https://www.bilibili.com/video/BV1M8c7zSEBQ/?spm_id_from=333.1007.tianma.3-2-6.click&vd_source=cd3ecdc981801d2a54a308d648c1d491"
    bvid = "BV1M8c7zSEBQ"
    print(f"🎯 目标视频: {video_url}")
    print(f"📝 BVID: {bvid}")
    
    # 尝试加载 Cookie
    cookie = load_cookie_from_file()
    
    if not cookie:
        print("\n⚠️ 没有找到 Cookie，将尝试无 Cookie 访问（可能失败）")
        print("💡 如需完整测试，请：")
        print("   1. 运行 BBDown 登录获取 Cookie")
        print("   2. 或手动将 Cookie 保存到 tools/BBDown/cookie.txt")
    
    # 创建 API 实例
    api = BilibiliAPI(cookie=cookie)
    
    try:
        # 步骤1：获取视频信息
        print(f"\n📊 步骤1：获取视频信息...")
        video_info = api.get_video_info(bvid)
        
        aid = video_info['aid']
        cid = video_info['cid']
        title = video_info['title']
        
        print(f"✅ 视频信息:")
        print(f"   - 标题: {title}")
        print(f"   - AID: {aid}")
        print(f"   - CID: {cid}")
        
        # 步骤2：获取播放器信息
        print(f"\n🎬 步骤2：获取播放器信息...")
        player_info = api.get_player_info(aid, cid)
        subtitles = player_info.get('subtitles', [])
        
        print(f"📋 播放器 API 返回的字幕列表: {len(subtitles)} 个")
        
        if subtitles:
            for i, sub in enumerate(subtitles):
                lan = sub.get('lan', '')
                lan_doc = sub.get('lan_doc', '')
                subtitle_url = sub.get('subtitle_url', '')
                print(f"   [{i+1}] {lan} - {lan_doc}")
                print(f"       URL: {'有' if subtitle_url else '无'}")
        else:
            print("   没有找到字幕列表")
        
        # 步骤3：尝试 AI 字幕 API
        print(f"\n🤖 步骤3：尝试 AI 字幕 API...")
        try:
            ai_subtitle_url = api.get_ai_subtitle_url(aid, cid)
            
            if ai_subtitle_url:
                print(f"✅ AI 字幕 API 成功!")
                print(f"   - AI 字幕 URL: {ai_subtitle_url}")
                
                # 下载 AI 字幕
                print(f"\n📥 步骤4：下载 AI 字幕...")
                subtitle_data = api.download_subtitle(ai_subtitle_url)
                
                if subtitle_data and subtitle_data.get('body'):
                    subtitle_list = subtitle_data['body']
                    print(f"✅ AI 字幕下载成功，共 {len(subtitle_list)} 条")
                    
                    # 显示前5条字幕
                    print(f"\n📖 AI 字幕预览:")
                    for i, item in enumerate(subtitle_list[:5]):
                        content = item.get('content', '')
                        start_time = item.get('from', 0)
                        end_time = item.get('to', 0)
                        print(f"   [{i+1}] {start_time:.2f}s-{end_time:.2f}s: {content}")
                    
                    # 保存字幕文件
                    os.makedirs('output', exist_ok=True)
                    import re
                    safe_title = re.sub(r'[<>:"/\\|?*]', '_', title)
                    filename = f"output/{safe_title}_{bvid}_AI.srt"
                    
                    # 格式化为 SRT
                    srt_content = api._format_subtitles_to_srt(subtitle_list)
                    with open(filename, 'w', encoding='utf-8') as f:
                        f.write(srt_content)
                    
                    print(f"💾 AI 字幕已保存到: {filename}")
                    return True
                else:
                    print(f"❌ AI 字幕内容为空")
            else:
                print(f"❌ AI 字幕 API 返回空 URL")
                
        except Exception as e:
            print(f"❌ AI 字幕 API 调用失败: {e}")
        
        # 步骤4：使用完整流程函数测试
        print(f"\n🔄 步骤4：使用完整流程函数测试...")
        result = api.get_subtitle_with_ai_fallback(bvid, cid)
        
        if result.get('success'):
            print(f"✅ 完整流程成功!")
            metadata = result.get('metadata', {})
            subtitles = result.get('subtitles', [])
            print(f"   - 语言: {metadata.get('lan')} - {metadata.get('lan_doc')}")
            print(f"   - 字幕条数: {len(subtitles)}")
            return True
        else:
            error_msg = result.get('message', '未知错误')
            print(f"❌ 完整流程失败: {error_msg}")
        
        return False
        
    except Exception as e:
        print(f"❌ 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主函数。"""
    # 设置日志
    setup_logging()
    
    # 运行测试
    success = test_ai_subtitle()
    
    if success:
        print(f"\n🎉 测试成功！AI 字幕功能正常工作")
    else:
        print(f"\n⚠️ 测试未完全成功")
        print(f"💡 可能的原因:")
        print(f"   1. 需要有效的 Cookie 才能访问 AI 字幕 API")
        print(f"   2. 该视频的 AI 字幕可能需要特殊权限")
        print(f"   3. B 站 API 可能有变化")
    
    print(f"\n✨ 详细日志请查看 ai_subtitle_test.log")

if __name__ == "__main__":
    main()