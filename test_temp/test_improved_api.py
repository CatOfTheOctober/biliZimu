#!/usr/bin/env python3
"""测试改进后的 BilibiliAPI 功能。"""

import sys
import os
import logging

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from bilibili_extractor.modules.bilibili_api import BilibiliAPI
from bilibili_extractor.core.config import Config

def setup_logging():
    """设置日志。"""
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('test_improved_api.log', encoding='utf-8')
        ]
    )

def test_get_aid_from_bvid():
    """测试从 bvid 获取 aid 功能。"""
    print("\n=== 测试 get_aid_from_bvid 功能 ===")
    
    # 创建 API 实例
    api = BilibiliAPI()
    
    # 测试视频
    test_bvid = "BV1SpqhBbE7F"
    
    try:
        aid = api.get_aid_from_bvid(test_bvid)
        print(f"✅ 成功获取 aid: {aid}")
        return aid
    except Exception as e:
        print(f"❌ 获取 aid 失败: {e}")
        return None

def test_wbi_request_handling():
    """测试 WBI 请求特殊处理。"""
    print("\n=== 测试 WBI 请求特殊处理 ===")
    
    # 创建 API 实例
    api = BilibiliAPI()
    
    # 测试参数
    aid = 1101493164  # BV1SpqhBbE7F 的 aid
    cid = 1459078442  # 对应的 cid
    
    try:
        player_info = api.get_player_info(aid, cid)
        subtitles = player_info.get('subtitles', [])
        print(f"✅ WBI 请求成功: 找到 {len(subtitles)} 个字幕")
        
        for i, subtitle in enumerate(subtitles):
            print(f"  字幕[{i}]: {subtitle.get('lan')} - {subtitle.get('lan_doc')}")
        
        return player_info
    except Exception as e:
        print(f"❌ WBI 请求失败: {e}")
        return None

def test_complete_subtitle_flow():
    """测试完整的字幕获取流程。"""
    print("\n=== 测试完整字幕获取流程 ===")
    
    # 创建 API 实例
    api = BilibiliAPI()
    
    # 测试视频
    test_bvid = "BV1SpqhBbE7F"
    test_cid = 1459078442
    
    try:
        result = api.get_subtitle_with_ai_fallback(test_bvid, test_cid)
        
        if result.get('success'):
            metadata = result.get('metadata', {})
            subtitles = result.get('subtitles', [])
            
            print(f"✅ 字幕获取成功:")
            print(f"  - aid: {metadata.get('aid')}")
            print(f"  - bvid: {metadata.get('bvid')}")
            print(f"  - cid: {metadata.get('cid')}")
            print(f"  - 语言: {metadata.get('lan')} - {metadata.get('lan_doc')}")
            print(f"  - 字幕条数: {len(subtitles)}")
            
            # 显示前3条字幕
            if subtitles:
                print("  - 前3条字幕:")
                for i, subtitle in enumerate(subtitles[:3]):
                    content = subtitle.get('content', '')
                    start_time = subtitle.get('from', 0)
                    print(f"    [{i+1}] {start_time:.2f}s: {content}")
        else:
            print(f"❌ 字幕获取失败: {result.get('message')}")
        
        return result
    except Exception as e:
        print(f"❌ 完整流程测试失败: {e}")
        return None

def main():
    """主函数。"""
    print("🚀 开始测试改进后的 BilibiliAPI")
    
    # 设置日志
    setup_logging()
    
    # 测试各个功能
    aid = test_get_aid_from_bvid()
    
    if aid:
        test_wbi_request_handling()
    
    test_complete_subtitle_flow()
    
    print("\n✨ 测试完成！详细日志请查看 test_improved_api.log")

if __name__ == "__main__":
    main()