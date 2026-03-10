"""手动测试脚本 - 核心功能验证

此脚本用于手动测试：
1. AuthManager的Cookie检测和登录功能
2. BilibiliAPI的各个API调用
3. SubtitleParser解析不同格式字幕
"""

import sys
import logging
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from src.bilibili_extractor.core.config import Config
from src.bilibili_extractor.modules.auth_manager import AuthManager
from src.bilibili_extractor.modules.bilibili_api import BilibiliAPI
from src.bilibili_extractor.modules.subtitle_parser import SubtitleParser


def test_auth_manager():
    """测试AuthManager功能"""
    print("\n" + "="*60)
    print("测试 1: AuthManager - Cookie检测和管理")
    print("="*60)
    
    config = Config()
    auth_manager = AuthManager(config)
    
    # 测试1.1: 查找BBDown Cookie路径
    print("\n[测试1.1] 查找BBDown Cookie路径...")
    cookie_path = auth_manager.get_bbdown_cookie_path('web')
    if cookie_path:
        print(f"✓ 找到Cookie文件: {cookie_path}")
    else:
        print("✗ 未找到Cookie文件（这是正常的，如果您还没有登录）")
    
    # 测试1.2: 检查Cookie是否存在
    print("\n[测试1.2] 检查Cookie是否存在...")
    cookie_exists = auth_manager.check_cookie('web')
    if cookie_exists:
        print(f"✓ Cookie存在: {auth_manager.get_cookie_path()}")
        
        # 测试1.3: 读取Cookie内容
        print("\n[测试1.3] 读取Cookie内容...")
        try:
            cookie_content = auth_manager.read_cookie_content(auth_manager.get_cookie_path())
            # 只显示前50个字符
            print(f"✓ Cookie内容（前50字符）: {cookie_content[:50]}...")
            
            # 测试1.4: 验证Cookie格式
            print("\n[测试1.4] 验证Cookie格式...")
            is_valid = auth_manager.validate_cookie_format(auth_manager.get_cookie_path(), 'web')
            if is_valid:
                print("✓ Cookie格式有效")
            else:
                print("✗ Cookie格式无效")
        except Exception as e:
            print(f"✗ 读取Cookie失败: {e}")
    else:
        print("✗ Cookie不存在")
        print("提示: 您可以运行 'BBDown login' 来登录")
    
    return cookie_exists


def test_bilibili_api(has_cookie=False):
    """测试BilibiliAPI功能"""
    print("\n" + "="*60)
    print("测试 2: BilibiliAPI - API调用（含WBI签名）")
    print("="*60)
    
    # 使用测试视频: BV1bicgzaEA3
    test_bvid = "BV1bicgzaEA3"
    
    # 如果有Cookie，读取它
    cookie = None
    if has_cookie:
        config = Config()
        auth_manager = AuthManager(config)
        auth_manager.check_cookie('web')
        cookie_path = auth_manager.get_cookie_path()
        if cookie_path:
            cookie = auth_manager.read_cookie_content(cookie_path)
    
    api = BilibiliAPI(cookie)
    
    # 测试2.1: 获取视频信息
    print(f"\n[测试2.1] 获取视频信息 (BVID: {test_bvid})...")
    try:
        video_info = api.get_video_info(test_bvid)
        print(f"✓ 视频标题: {video_info['title']}")
        print(f"✓ AID: {video_info['aid']}")
        print(f"✓ CID: {video_info['cid']}")
        print(f"✓ 时长: {video_info['duration']}秒")
        
        aid = video_info['aid']
        cid = video_info['cid']
        
        # 测试2.2: 获取播放器信息（使用旧版API）
        print(f"\n[测试2.2] 获取播放器信息（使用旧版v2 API）...")
        try:
            player_info = api.get_player_info(aid, cid)
            subtitles = player_info['subtitles']
            print(f"✓ 找到 {len(subtitles)} 个字幕")
            
            for i, subtitle in enumerate(subtitles):
                print(f"  字幕 {i+1}: {subtitle.get('lan_doc', 'Unknown')} ({subtitle.get('lan', 'Unknown')})")
                print(f"    URL: {subtitle.get('subtitle_url', 'Empty')[:50]}...")
                if subtitle.get('ai_status'):
                    print(f"    AI状态: {subtitle.get('ai_status')}")
            
            # 测试2.3: 如果有AI字幕且URL为空，调用AI字幕API
            ai_subtitle = next((s for s in subtitles if s.get('lan', '').startswith('ai-')), None)
            if ai_subtitle and not ai_subtitle.get('subtitle_url'):
                print(f"\n[测试2.3] 获取AI字幕URL...")
                try:
                    ai_url = api.get_ai_subtitle_url(aid, cid)
                    if ai_url:
                        print(f"✓ AI字幕URL: {ai_url[:50]}...")
                    else:
                        print("✗ AI字幕URL为空")
                except Exception as e:
                    print(f"✗ 获取AI字幕URL失败: {e}")
            
            # 测试2.4: 下载字幕
            if subtitles and subtitles[0].get('subtitle_url'):
                print(f"\n[测试2.4] 下载字幕...")
                try:
                    subtitle_url = subtitles[0]['subtitle_url']
                    subtitle_data = api.download_subtitle(subtitle_url)
                    print(f"✓ 字幕下载成功")
                    print(f"  字幕条目数: {len(subtitle_data.get('body', []))}")
                    
                    return subtitle_data
                except Exception as e:
                    print(f"✗ 下载字幕失败: {e}")
            
        except Exception as e:
            print(f"✗ 获取播放器信息失败: {e}")
            import traceback
            traceback.print_exc()
        
    except Exception as e:
        print(f"✗ 获取视频信息失败: {e}")
    
    return None


def test_subtitle_parser(subtitle_data=None):
    """测试SubtitleParser功能"""
    print("\n" + "="*60)
    print("测试 3: SubtitleParser - 字幕解析")
    print("="*60)
    
    if subtitle_data is None:
        print("✗ 没有字幕数据可供测试")
        print("提示: 使用模拟数据进行测试...")
        
        # 使用模拟的AI字幕数据
        subtitle_data = {
            "body": [
                {"from": 0.0, "to": 2.5, "content": "测试字幕1"},
                {"from": 2.5, "to": 5.0, "content": "测试字幕2"},
                {"from": 5.0, "to": 7.5, "content": "测试字幕3"},
            ]
        }
    
    # 测试3.1: 检测字幕格式
    print("\n[测试3.1] 检测字幕格式...")
    is_ai = SubtitleParser.is_ai_subtitle_format(subtitle_data)
    print(f"✓ 字幕格式: {'AI字幕' if is_ai else '普通字幕'}")
    
    # 测试3.2: 解析字幕
    print("\n[测试3.2] 解析字幕...")
    try:
        segments = SubtitleParser.parse_subtitle(subtitle_data)
        print(f"✓ 解析成功，共 {len(segments)} 个片段")
        
        # 显示前3个片段
        for i, segment in enumerate(segments[:3]):
            print(f"  片段 {i+1}: [{segment.start_time:.2f}s - {segment.end_time:.2f}s] {segment.text[:30]}...")
        
        # 测试3.3: 验证时间戳
        print("\n[测试3.3] 验证时间戳...")
        all_valid = all(seg.start_time < seg.end_time for seg in segments)
        if all_valid:
            print("✓ 所有片段的时间戳都有效 (start_time < end_time)")
        else:
            print("✗ 发现无效的时间戳")
        
        # 测试3.4: 验证排序
        print("\n[测试3.4] 验证排序...")
        is_sorted = all(segments[i].start_time <= segments[i+1].start_time 
                       for i in range(len(segments)-1))
        if is_sorted:
            print("✓ 片段按start_time升序排序")
        else:
            print("✗ 片段排序不正确")
        
        # 测试3.5: 验证无重叠
        print("\n[测试3.5] 验证无重叠...")
        no_overlap = all(segments[i].end_time <= segments[i+1].start_time 
                        for i in range(len(segments)-1))
        if no_overlap:
            print("✓ 相邻片段无重叠")
        else:
            print("⚠ 发现重叠片段（这可能是正常的）")
        
    except Exception as e:
        print(f"✗ 解析字幕失败: {e}")


def main():
    """主测试函数"""
    print("\n" + "="*60)
    print("B站AI字幕支持和Cookie管理 - 核心功能验证")
    print("="*60)
    
    try:
        # 测试1: AuthManager
        has_cookie = test_auth_manager()
        
        # 测试2: BilibiliAPI
        subtitle_data = test_bilibili_api(has_cookie)
        
        # 测试3: SubtitleParser
        test_subtitle_parser(subtitle_data)
        
        print("\n" + "="*60)
        print("测试完成！")
        print("="*60)
        print("\n请检查上面的测试结果。")
        print("如果有 ✗ 标记，请查看错误信息并进行调整。")
        
    except KeyboardInterrupt:
        print("\n\n测试被用户中断")
    except Exception as e:
        print(f"\n\n测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
