"""Command-line interface for bilibili-extractor.

Validates: Requirements 10.1, 10.2, 10.5, 10.6
"""

import argparse
import sys
import time
from pathlib import Path
from typing import Optional

# Add src directory to sys.path to ensure modules are found (Requirement 10.1)
src_path = str(Path(__file__).parent.parent.absolute())
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from bilibili_extractor.core.config import Config, ConfigLoader
from bilibili_extractor.core.extractor import TextExtractor, ExtractionResult
from bilibili_extractor.modules.output_formatter import OutputFormatter
from bilibili_extractor.modules.url_validator import URLValidationError
from bilibili_extractor.modules.subtitle_fetcher import SubtitleNotFoundError
from bilibili_extractor.utils.logger import Logger


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments.
    
    Validates: Requirements 11.2, 11.3
    
    Returns:
        Parsed arguments namespace
    """
    parser = argparse.ArgumentParser(
        description="Extract text from Bilibili videos",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Extract text from a video (uses official subtitles if available)
  %(prog)s "https://www.bilibili.com/video/BV1xx411c7mD"
  
  # Specify output format
  %(prog)s "https://www.bilibili.com/video/BV1xx411c7mD" --format json
  
  # Use ASR with INT8 optimization
  %(prog)s "https://www.bilibili.com/video/BV1xx411c7mD" --use-int8
  
  # Batch processing
  %(prog)s --batch urls.txt --output-dir ./outputs
  
  # Access premium content with cookie
  %(prog)s "https://www.bilibili.com/video/BV1xx411c7mD" --cookie cookie.txt

For more information, visit: https://github.com/your-repo/bilibili-extractor
        """,
    )

    # Positional arguments
    parser.add_argument("url", nargs="?", help="Bilibili video URL")

    # Input options
    parser.add_argument(
        "--batch",
        type=str,
        metavar="FILE",
        help="File containing list of URLs (one per line)",
    )

    # Configuration options
    parser.add_argument(
        "--config",
        type=str,
        metavar="FILE",
        help="Path to YAML config file",
    )
    parser.add_argument(
        "--cookie",
        type=str,
        metavar="FILE",
        help="Path to cookie file (for premium content)",
    )
    parser.add_argument(
        "--login",
        action="store_true",
        help="Force BBDown login before extraction",
    )
    parser.add_argument(
        "--check-cookie",
        action="store_true",
        help="Check cookie status and exit",
    )
    parser.add_argument(
        "--clear-cache",
        action="store_true",
        help="Clear subtitle cache and exit",
    )
    parser.add_argument(
        "--no-auto-login",
        action="store_true",
        help="Disable automatic login when cookie is invalid",
    )
    parser.add_argument(
        "--temp-dir",
        type=str,
        metavar="DIR",
        help="Temporary directory for downloads (default: ./temp)",
    )
    parser.add_argument(
        "--video-quality",
        choices=["480P", "720P", "1080P"],
        help="Video quality for download (default: 720P)",
    )

    # ASR options
    parser.add_argument(
        "--asr-engine",
        choices=["funasr", "whisper"],
        help="ASR engine to use (default: funasr)",
    )
    parser.add_argument(
        "--funasr-model",
        type=str,
        help="FunASR model name (default: paraformer-zh)",
    )
    parser.add_argument(
        "--whisper-model",
        choices=["tiny", "base", "small", "medium", "large"],
        help="Whisper model size (default: base)",
    )
    parser.add_argument(
        "--language",
        type=str,
        metavar="CODE",
        help="Language code for Whisper (e.g., zh, en)",
    )
    parser.add_argument(
        "--use-int8",
        action="store_true",
        help="Use INT8 quantization for FunASR (2-3x speed boost)",
    )
    parser.add_argument(
        "--use-onnx",
        action="store_true",
        help="Use ONNX Runtime for FunASR (3-4x speed boost)",
    )

    # Output options
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        metavar="FILE",
        help="Output file path",
    )
    parser.add_argument(
        "--format",
        "-f",
        choices=["srt", "json", "txt", "markdown"],
        default="txt",
        help="Output format (default: txt)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        metavar="DIR",
        help="Output directory (default: ./output)",
    )

    # Other options
    parser.add_argument(
        "--keep-temp",
        action="store_true",
        help="Keep temporary files after processing",
    )
    parser.add_argument(
        "--enable-ocr",
        action="store_true",
        help="Enable OCR for hard subtitles (experimental)",
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Log level (default: INFO)",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="bilibili-extractor 1.0.0",
    )

    return parser.parse_args()


def load_config(args: argparse.Namespace) -> Config:
    """Load configuration from file and command-line arguments.
    
    Args:
        args: Parsed command-line arguments
        
    Returns:
        Merged configuration object
    """
    # Load from config file if provided
    if args.config:
        config_path = Path(args.config)
        if not config_path.exists():
            print(f"Error: Config file not found: {args.config}", file=sys.stderr)
            sys.exit(1)
        
        file_config = ConfigLoader.load_from_file(config_path)
    else:
        file_config = Config()
    
    # Load from command-line arguments
    args_config = ConfigLoader.load_from_args(args)
    
    # Merge configurations (CLI args override file config)
    config = ConfigLoader.merge_configs(file_config, args_config)
    
    # Validate configuration
    ConfigLoader.validate_config(config)
    
    return config


def format_time(seconds: float) -> str:
    """Format time duration for display.
    
    Args:
        seconds: Time in seconds
        
    Returns:
        Formatted time string (e.g., "3.45s" or "2m 15s")
    """
    if seconds < 60:
        return f"{seconds:.2f}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = seconds % 60
        return f"{minutes}m {secs:.0f}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"


def display_summary(result, output_path: Path, total_time: float) -> None:
    """Display extraction summary report.
    
    Validates: Requirements 10.5, 10.6
    
    Args:
        result: ExtractionResult object
        output_path: Path to output file
        total_time: Total processing time in seconds
    """
    print("\n" + "=" * 50)
    print("=== Extraction Complete ===")
    print("=" * 50)
    print(f"Video ID: {result.video_info.video_id}")
    
    # 显示文本来源
    if result.method == "subtitle":
        # 检查是否为AI字幕
        if result.segments and result.segments[0].source == 'subtitle':
            print(f"Method: Bilibili API (Subtitle)")
        else:
            print(f"Method: Subtitle")
    else:
        print(f"Method: ASR ({result.metadata.get('asr_engine', 'unknown')})")
    
    print(f"Segments: {len(result.segments)}")
    print(f"Processing Time: {format_time(result.processing_time)}")
    print(f"Total Time: {format_time(total_time)}")
    print(f"Output: {output_path}")
    print("=" * 50)


def save_output(result, output_path: Path, output_format: str) -> None:
    """Save extraction result to file.
    
    Args:
        result: ExtractionResult object
        output_path: Path to output file
        output_format: Output format (srt/json/txt/markdown)
    """
    # Format output based on format type
    if output_format == "srt":
        content = OutputFormatter.to_srt(result.segments)
    elif output_format == "json":
        content = OutputFormatter.to_json(result)
    elif output_format == "txt":
        content = OutputFormatter.to_txt(result.segments)
    elif output_format == "markdown":
        content = OutputFormatter.to_markdown(result)
    else:
        raise ValueError(f"Unsupported output format: {output_format}")
    
    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Write to file
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)


def process_single_url(url: str, config: Config, args: argparse.Namespace) -> int:
    """Process a single video URL.
    
    Validates: Requirements 10.1, 10.2, 10.5, 10.6
    
    Args:
        url: Bilibili video URL
        config: Configuration object
        args: Command-line arguments
        
    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    start_time = time.time()
    
    try:
        # Step 1: Create extractor (Requirement 10.1)
        print(f"[INFO] Processing video URL: {url}")
        extractor = TextExtractor(config)
        
        # Step 2: Extract text (Requirement 10.2)
        print("[INFO] Starting extraction...")
        try:
            result = extractor.extract(url, force_asr=False)
        except SubtitleNotFoundError:
            print("\n[!] 未找到 API 字幕 (AI字幕下载失败)。")
            choice = input("是否进一步下载视频用于 ASR 模型识别字幕? (y/N): ").strip().lower()
            if choice == 'y':
                print("[INFO] 正在启动视频下载与 ASR 识别流程...")
                result = extractor.extract(url, force_asr=True)
            else:
                print("[INFO] 用户取消。程序退出。")
                return 0
        
        # Step 3: Determine output path
        if args.output:
            output_path = Path(args.output)
        else:
            # Generate output filename from video ID
            video_id = result.video_info.video_id
            output_dir = config.resolve_path(config.output_dir)
            output_path = output_dir / f"{video_id}.{config.output_format}"
        
        # Step 4: Save output
        print(f"[INFO] Saving output to {output_path}...")
        save_output(result, output_path, config.output_format)
        
        # Step 5: Display summary (Requirements 10.5, 10.6)
        total_time = time.time() - start_time
        display_summary(result, output_path, total_time)
        
        return 0
    
    except URLValidationError as e:
        print(f"\n[ERROR] Invalid URL: {e}", file=sys.stderr)
        print("Please provide a valid Bilibili video URL.", file=sys.stderr)
        return 1
    
    except SubtitleNotFoundError as e:
        print(f"\n[ERROR] No subtitles found: {e}", file=sys.stderr)
        print("ASR support will be available in future versions.", file=sys.stderr)
        return 1
    
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}", file=sys.stderr)
        print("Please check the logs for more details.", file=sys.stderr)
        return 1


def process_batch_urls(batch_file: str, config: Config, args: argparse.Namespace) -> int:
    """Process multiple video URLs from a file.
    
    Validates: Requirements 12.1, 12.5, 12.6
    
    Args:
        batch_file: Path to file containing URLs (one per line)
        config: Configuration object
        args: Command-line arguments
        
    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    start_time = time.time()
    
    try:
        # Read URLs from file (Requirement 12.1)
        batch_path = Path(batch_file)
        if not batch_path.exists():
            print(f"[ERROR] Batch file not found: {batch_file}", file=sys.stderr)
            return 1
        
        with open(batch_path, "r", encoding="utf-8") as f:
            urls = [line.strip() for line in f if line.strip() and not line.startswith("#")]
        
        if not urls:
            print("[ERROR] No URLs found in batch file", file=sys.stderr)
            return 1
        
        print(f"[INFO] Found {len(urls)} URLs in batch file")
        print(f"[INFO] Starting batch processing...")
        
        # Create extractor
        extractor = TextExtractor(config)
        
        # Process all URLs (Requirement 12.2)
        results = extractor.extract_batch(urls)
        
        # Save outputs for successful extractions (Requirement 12.3)
        output_dir = config.resolve_path(config.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"\n[INFO] Saving outputs to {output_dir}...")
        for result in results:
            video_id = result.video_info.video_id
            output_path = output_dir / f"{video_id}.{config.output_format}"
            save_output(result, output_path, config.output_format)
            print(f"  ✓ Saved: {output_path}")
        
        # Display batch summary (Requirements 12.5, 12.6)
        total_time = time.time() - start_time
        success_count = len(results)
        failed_count = len(urls) - success_count
        
        print("\n" + "=" * 60)
        print("=== Batch Processing Complete ===")
        print("=" * 60)
        print(f"Total videos: {len(urls)}")
        print(f"Successful: {success_count}")
        print(f"Failed: {failed_count}")
        print(f"Total time: {format_time(total_time)}")
        print(f"Output directory: {output_dir}")
        print("=" * 60)
        
        # Return success if at least one video was processed
        return 0 if success_count > 0 else 1
    
    except Exception as e:
        print(f"\n[ERROR] Batch processing failed: {e}", file=sys.stderr)
        return 1


def clear_cache(config: Config) -> int:
    """清除字幕缓存。
    
    Args:
        config: Configuration object
        
    Returns:
        Exit code (0 for success, 1 for failure)
    """
    import os
    import shutil
    
    print("\n" + "=" * 50)
    print("=== Clearing Subtitle Cache ===")
    print("=" * 50)
    
    # 获取输出目录
    output_dir = config.output_dir or "./output"
    
    try:
        if os.path.exists(output_dir):
            # 列出要删除的文件
            files = os.listdir(output_dir)
            if files:
                print(f"\nFound {len(files)} file(s) in {output_dir}:")
                for file in files:
                    file_path = os.path.join(output_dir, file)
                    if os.path.isfile(file_path):
                        size = os.path.getsize(file_path)
                        print(f"  - {file} ({size} bytes)")
                
                # 删除所有文件
                for file in files:
                    file_path = os.path.join(output_dir, file)
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                        print(f"\n✓ Deleted: {file}")
                
                print(f"\n✓ Cache cleared successfully")
            else:
                print(f"\nNo files found in {output_dir}")
        else:
            print(f"\nOutput directory does not exist: {output_dir}")
            return 1
    except Exception as e:
        print(f"\n✗ Error clearing cache: {e}")
        return 1
    
    print("=" * 50)
    return 0


def check_cookie_status(config: Config) -> int:
    """检查Cookie状态。
    
    Args:
        config: Configuration object
        
    Returns:
        Exit code (0 for success, 1 for failure)
    """
    from bilibili_extractor.modules.auth_manager import AuthManager
    
    print("\n" + "=" * 50)
    print("=== Cookie Status Check ===")
    print("=" * 50)
    
    auth_manager = AuthManager(config)
    
    # 检查Cookie是否存在
    if auth_manager.check_cookie():
        cookie_path = auth_manager.get_cookie_path()
        print(f"Cookie file: {cookie_path}")
        print(f"Status: ✓ Found")
        
        # 验证Cookie格式
        if auth_manager.validate_cookie_format(cookie_path):
            print(f"Format: ✓ Valid")
            
            # 读取Cookie内容（只显示前缀）
            try:
                content = auth_manager.read_cookie_content(cookie_path)
                if 'SESSDATA=' in content:
                    sessdata_start = content.find('SESSDATA=') + 9
                    sessdata_prefix = content[sessdata_start:sessdata_start+10]
                    print(f"SESSDATA: {sessdata_prefix}... (hidden)")
                print(f"\n✓ Cookie is valid and ready to use")
            except Exception as e:
                print(f"Error reading cookie: {e}")
                return 1
        else:
            print(f"Format: ✗ Invalid")
            print(f"\n✗ Cookie format is invalid")
            return 1
    else:
        print(f"Status: ✗ Not found")
        print(f"\nNo cookie file found. Use --login to authenticate.")
        return 1
    
    print("=" * 50)
    return 0


def perform_login(config: Config) -> int:
    """执行BBDown登录。
    
    Args:
        config: Configuration object
        
    Returns:
        Exit code (0 for success, 1 for failure)
    """
    from bilibili_extractor.modules.auth_manager import AuthManager
    from bilibili_extractor.core.exceptions import AuthenticationError
    
    print("\n" + "=" * 50)
    print("=== BBDown Login ===")
    print("=" * 50)
    
    auth_manager = AuthManager(config)
    
    try:
        login_type = config.login_type if hasattr(config, 'login_type') else 'web'
        auth_manager.login_with_bbdown(login_type)
        print("\n✓ Login successful!")
        return 0
    except AuthenticationError as e:
        print(f"\n✗ Login failed: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}", file=sys.stderr)
        return 1


def main() -> int:
    """Main CLI entry point.
    
    Validates: Requirements 10.1, 10.2, 10.5, 10.6, 12.1, 12.5, 12.6

    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    # 打印引导提示 (针对用户反馈的 CLI 环境隔离问题)
    print("\n" + "="*60)
    print("💡 温馨提示: 推荐使用项目根目录下的 '下载字幕.py' 脚本")
    print("   该脚本经过针对性优化，支持自动 ASR 降级和 WBI 签名处理，体验更佳。")
    print("   执行指令: python 下载字幕.py")
    print("="*60 + "\n")

    # Parse arguments
    args = parse_arguments()
    
    # Load configuration
    try:
        config = load_config(args)
    except Exception as e:
        print(f"Error loading configuration: {e}", file=sys.stderr)
        return 1
    
    # Handle --check-cookie command
    if args.check_cookie:
        return check_cookie_status(config)
    
    # Handle --clear-cache command
    if args.clear_cache:
        return clear_cache(config)
    
    # Handle --login command
    if args.login:
        return perform_login(config)
    
    # Validate arguments
    if not args.url and not args.batch:
        print("Error: Either URL or --batch must be provided", file=sys.stderr)
        return 1
    
    # Process URL(s)
    if args.url:
        # Single URL processing
        return process_single_url(args.url, config, args)
    else:
        # Batch processing (Requirement 12.1)
        return process_batch_urls(args.batch, config, args)


if __name__ == "__main__":
    sys.exit(main())
