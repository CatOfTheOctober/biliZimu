# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **AI字幕支持**：自动获取B站AI生成的字幕
  - 集成B站播放器API和AI字幕API
  - 优先获取AI字幕（ai-zh），降级到普通字幕
  - 新增BilibiliAPI模块封装API调用
  - 新增SubtitleParser模块统一解析字幕格式
- **Cookie管理功能**：自动化Cookie管理和BBDown登录集成
  - 新增AuthManager模块管理Cookie
  - 自动检测BBDown Cookie文件（BBDown.data）
  - 支持`--login`命令进行BBDown扫码登录
  - 支持`--check-cookie`命令检查Cookie状态
  - 支持`--no-auto-login`禁用自动登录
- **字幕获取优先级机制**：Bilibili API（AI字幕+普通字幕）→ ASR
- **新增异常类**：AuthenticationError, CookieNotFoundError, BilibiliAPIError等
- **API重试机制**：自动重试失败的API请求（最多3次，指数退避）

### Changed
- 更新TextExtractor集成Cookie管理和Bilibili API
- 更新SubtitleFetcher实现新的字幕获取优先级
- 更新CLI显示字幕来源信息（Bilibili API / ASR）
- 更新Config支持Cookie相关配置（auto_login, login_type）
- 改进错误处理和日志记录

### Fixed
- ASR库缺失时的优雅错误处理
  - 当FunASR或Whisper未安装时，系统仍可正常处理有字幕的视频
  - 处理无字幕视频时，提供清晰的安装指引
  - 添加了新的单元测试验证错误处理逻辑

### Documentation
- 更新README添加AI字幕和Cookie管理说明
- 更新COOKIE_GUIDE.md文档
- 添加BBDown Cookie机制详解文档

## [1.0.0] - 2026-02-26

### Added
- Initial release of Bilibili Video Text Extractor
- Two-stage text extraction: official subtitles → ASR fallback
- BBDown integration for subtitle and video downloading
- Dual ASR engine support: FunASR (Chinese-optimized) and Whisper (multilingual)
- Cookie authentication for premium/member-only content
- Multiple output formats: SRT, JSON, TXT, Markdown
- CPU optimization: INT8 quantization and ONNX Runtime support
- Batch processing for multiple videos
- Automatic resource cleanup
- Comprehensive logging system
- Command-line interface with extensive options
- Configuration file support (YAML)
- 198 unit and integration tests with 79% code coverage

### Features

#### Core Functionality
- URL validation for Bilibili videos (BV/av format, short links)
- Official subtitle detection and download (BBDown --sub-only)
- Subtitle parsing (SRT, JSON, XML formats)
- Video download with quality selection (480P/720P/1080P)
- Audio extraction (16kHz, mono, WAV format)
- ASR transcription with progress callbacks
- Multi-format output generation

#### ASR Engines
- **FunASR**: Chinese-optimized, 2-3x faster than Whisper
  - paraformer-zh model with VAD and punctuation prediction
  - INT8 quantization support (2-3x speed boost)
  - ONNX Runtime support (3-4x speed boost)
- **Whisper**: Multilingual support
  - Multiple model sizes (tiny/base/small/medium/large)
  - Language specification option

#### Batch Processing
- Process multiple videos from a file
- Error isolation (single failure doesn't affect others)
- Summary report with success/failure counts

#### User Experience
- Detailed progress logging
- Processing time statistics
- Automatic temporary file cleanup
- Configurable log levels
- Helpful error messages

### Technical Details
- Python 3.8+ support
- External dependencies: BBDown, FFmpeg
- Optional Python dependencies: funasr, openai-whisper, paddleocr
- Comprehensive test suite with property-based testing
- Type hints and documentation

### Known Limitations
- OCR for hard subtitles is not yet implemented (planned for future release)
- Progress bar visualization is basic (uses logging)
- No GUI interface (CLI only)

### Requirements
- Python 3.8 or higher
- BBDown (for downloading)
- FFmpeg (for audio extraction)
- Optional: FunASR or Whisper for ASR functionality

## [Unreleased]

### Planned Features
- OCR support for hard subtitles
- Enhanced progress bar with ETA
- Web interface
- Docker support
- More output formats
- Video metadata extraction
- Parallel batch processing

---

For more information, see the [README](README.md) and [documentation](docs/).
