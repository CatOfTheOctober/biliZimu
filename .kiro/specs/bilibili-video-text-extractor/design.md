# Design Document: Bilibili Video Text Extractor

## 1. Architecture Overview

### 1.1 System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Text Extractor (Main)                    │
│  - Orchestrates workflow                                     │
│  - Manages configuration                                     │
│  - Handles error recovery                                    │
└───────────┬─────────────────────────────────────────────────┘
            │
            ├──────────────┬──────────────┬──────────────┐
            ▼              ▼              ▼              ▼
    ┌──────────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
    │   Subtitle   │ │  Video   │ │  Audio   │ │   ASR    │
    │   Fetcher    │ │Downloader│ │Extractor │ │  Engine  │
    └──────────────┘ └──────────┘ └──────────┘ └──────────┘
            │              │              │              │
            └──────────────┴──────────────┴──────────────┘
                           │
                           ▼
                    ┌──────────────┐
                    │ OCR Engine   │
                    │  (Optional)  │
                    └──────────────┘
```

### 1.2 Processing Flow

1. URL Validation → Extract video ID
2. Check for official subtitles
3. If subtitles exist → Parse and output
4. If no subtitles → Download video → Extract audio → ASR
5. Optional: OCR for hard subtitles
6. Format output → Cleanup resources


## 2. Core Data Models

### 2.1 VideoInfo
```python
@dataclass
class VideoInfo:
    video_id: str          # BV号或av号
    title: str
    duration: int          # 秒
    has_subtitle: bool
    url: str
```

### 2.2 TextSegment
```python
@dataclass
class TextSegment:
    start_time: float      # 秒
    end_time: float        # 秒
    text: str
    confidence: float = 1.0  # 0-1，ASR置信度
    source: str = "subtitle"  # subtitle/asr/ocr
```

### 2.3 ExtractionResult
```python
@dataclass
class ExtractionResult:
    video_info: VideoInfo
    segments: List[TextSegment]
    method: str            # subtitle/asr/hybrid
    processing_time: float
    metadata: Dict[str, Any]
```

### 2.4 Config
```python
@dataclass
class Config:
    # 通用配置
    temp_dir: str = "./temp"
    output_dir: str = "./output"
    log_level: str = "INFO"
    keep_temp_files: bool = False
    
    # 下载配置
    cookie_file: Optional[str] = None
    video_quality: str = "720P"  # 480P/720P/1080P
    download_threads: int = 4
    
    # ASR配置
    asr_engine: str = "funasr"  # funasr/whisper
    funasr_model: str = "paraformer-zh"
    whisper_model: str = "base"
    language: Optional[str] = None
    
    # OCR配置
    enable_ocr: bool = False
    ocr_engine: str = "paddleocr"
    
    # 输出配置
    output_format: str = "srt"  # srt/json/txt/markdown
```


## 3. Module Design

### 3.1 URLValidator

**Purpose**: 验证和解析B站视频URL

**Interface**:
```python
class URLValidator:
    @staticmethod
    def validate(url: str) -> bool:
        """验证URL格式是否有效"""
        pass
    
    @staticmethod
    def extract_video_id(url: str) -> str:
        """从URL提取视频ID（BV号或av号）"""
        pass
    
    @staticmethod
    def normalize_url(url: str) -> str:
        """将短链接转换为标准URL"""
        pass
```

**Implementation Notes**:
- 支持格式：`bilibili.com/video/BV*`, `b23.tv/*`, `bilibili.com/video/av*`
- 使用正则表达式匹配
- 短链接需要HTTP请求获取重定向后的URL

**Properties**:
- Property 1: 对于有效URL，`extract_video_id(url)` 应返回一致的video_id
- Property 2: `validate(url)` 返回True当且仅当`extract_video_id(url)`不抛出异常

### 3.2 SubtitleFetcher

**Purpose**: 检测和下载官方字幕

**Interface**:
```python
class SubtitleFetcher:
    def __init__(self, config: Config):
        self.config = config
    
    def check_subtitle_availability(self, video_id: str) -> bool:
        """检查视频是否有官方字幕"""
        pass
    
    def download_subtitles(self, video_id: str) -> List[Path]:
        """使用BBDown下载字幕文件"""
        pass
    
    def parse_subtitle(self, subtitle_path: Path) -> List[TextSegment]:
        """解析字幕文件（SRT/JSON/XML）"""
        pass
```

**Implementation Notes**:
- 使用BBDown的`--sub-only`参数下载字幕
- 命令示例：`bbdown {video_url} --sub-only -c {cookie_file}`
- 支持解析SRT、JSON（B站API格式）、XML格式
- 优先选择中文字幕（zh-CN, zh-Hans）

**Properties**:
- Property 3: 解析后的segments时间戳应单调递增
- Property 4: 每个segment的start_time < end_time
- Property 5: 解析SRT后重新生成SRT应保持时间戳一致


### 3.3 VideoDownloader

**Purpose**: 下载B站视频文件

**Interface**:
```python
class VideoDownloader:
    def __init__(self, config: Config):
        self.config = config
    
    def download(self, video_id: str, progress_callback: Optional[Callable] = None) -> Path:
        """下载视频文件，返回本地路径"""
        pass
    
    def _download_with_bbdown(self, video_id: str) -> Path:
        """使用BBDown下载"""
        pass
    
    def _download_with_fallback(self, video_id: str) -> Path:
        """使用备用工具（you-get/yt-dlp）"""
        pass
```

**Implementation Notes**:
- 主要使用BBDown：`bbdown {video_url} -q {quality} -c {cookie_file} --work-dir {temp_dir}`
- 备用工具：you-get或yt-dlp
- 解析BBDown输出获取下载进度
- 多线程下载由BBDown自动处理

**Properties**:
- Property 6: 对同一video_id多次下载应得到相同的文件（内容hash一致）
- Property 7: 下载的视频文件应能被ffmpeg正常读取
- Property 8: 下载进度应从0%到100%单调递增

### 3.4 AudioExtractor

**Purpose**: 从视频提取音频流

**Interface**:
```python
class AudioExtractor:
    def extract(self, video_path: Path) -> Path:
        """从视频提取音频，返回音频文件路径"""
        pass
    
    def get_audio_duration(self, audio_path: Path) -> float:
        """获取音频时长（秒）"""
        pass
    
    def validate_audio(self, audio_path: Path) -> bool:
        """验证音频文件完整性"""
        pass
```

**Implementation Notes**:
- 使用ffmpeg-python库
- 转换参数：16kHz采样率，单声道，WAV格式
- 命令示例：`ffmpeg -i {video} -ar 16000 -ac 1 -vn {audio}.wav`
- 可选：使用低码率（32kbps）加快处理

**Properties**:
- Property 9: 提取的音频时长应与视频时长一致（±1秒）
- Property 10: 音频文件应能被标准音频库读取
- Property 11: 损坏的视频文件应返回明确错误而非生成无效音频


### 3.5 ASREngine

**Purpose**: 语音识别引擎抽象层

**Interface**:
```python
class ASREngine(ABC):
    @abstractmethod
    def transcribe(self, audio_path: Path, progress_callback: Optional[Callable] = None) -> List[TextSegment]:
        """转录音频为文字"""
        pass

class FunASREngine(ASREngine):
    def __init__(self, model: str = "paraformer-zh"):
        self.model = model
        self.vad_model = "fsmn-vad"
        self.punc_model = "ct-punc"
    
    def transcribe(self, audio_path: Path, progress_callback: Optional[Callable] = None) -> List[TextSegment]:
        """使用FunASR进行识别"""
        pass

class WhisperEngine(ASREngine):
    def __init__(self, model: str = "base", language: Optional[str] = None):
        self.model = model
        self.language = language
    
    def transcribe(self, audio_path: Path, progress_callback: Optional[Callable] = None) -> List[TextSegment]:
        """使用Whisper进行识别"""
        pass
```

**Implementation Notes**:
- FunASR使用funasr库，模型自动下载
- 启用VAD（语音活动检测）和标点预测
- Whisper使用openai-whisper库
- 返回带时间戳的文本段
- 提供置信度分数

**Properties**:
- Property 12: 识别结果的时间戳应单调递增
- Property 13: 所有时间戳应在[0, audio_duration]范围内
- Property 14: 对于清晰中文音频，FunASR准确率应高于Whisper
- Property 15: 识别进度应从0%到100%单调递增
- Property 16: 空音频文件应返回空列表而非错误


### 3.6 OCREngine (Optional)

**Purpose**: 识别视频中的硬字幕

**Interface**:
```python
class OCREngine:
    def __init__(self, config: Config):
        self.config = config
    
    def detect_subtitle_region(self, video_path: Path) -> Optional[Tuple[int, int, int, int]]:
        """检测字幕区域（x, y, width, height）"""
        pass
    
    def extract_text_from_frames(self, video_path: Path, region: Tuple) -> List[TextSegment]:
        """从关键帧提取文字"""
        pass
    
    def merge_with_asr(self, ocr_segments: List[TextSegment], asr_segments: List[TextSegment]) -> List[TextSegment]:
        """合并OCR和ASR结果"""
        pass
```

**Implementation Notes**:
- 使用PaddleOCR进行文字识别
- 采样关键帧（每秒1-2帧）
- 检测字幕区域以减少计算量
- 合并策略：时间戳对齐，优先ASR结果

**Properties**:
- Property 17: OCR结果的时间戳应对应实际帧时间
- Property 18: 合并后的segments时间戳应保持单调递增
- Property 19: 无字幕帧不应产生OCR结果

### 3.7 OutputFormatter

**Purpose**: 格式化输出结果

**Interface**:
```python
class OutputFormatter:
    @staticmethod
    def to_srt(segments: List[TextSegment]) -> str:
        """转换为SRT格式"""
        pass
    
    @staticmethod
    def to_json(result: ExtractionResult) -> str:
        """转换为JSON格式"""
        pass
    
    @staticmethod
    def to_txt(segments: List[TextSegment]) -> str:
        """转换为纯文本"""
        pass
    
    @staticmethod
    def to_markdown(result: ExtractionResult) -> str:
        """转换为Markdown格式"""
        pass
    
    @staticmethod
    def validate_format(content: str, format: str) -> bool:
        """验证输出格式正确性"""
        pass
```

**Implementation Notes**:
- SRT格式：标准字幕格式，包含序号、时间戳、文本
- JSON格式：包含完整元数据和segments
- TXT格式：纯文本，可选时间戳
- Markdown格式：带时间戳的列表

**Properties**:
- Property 20: SRT输出应能被标准SRT解析器解析
- Property 21: JSON输出应符合定义的schema
- Property 22: 格式转换应保持时间戳信息不丢失
- Property 23: 重新解析输出文件应得到等价的数据结构


### 3.8 ResourceManager

**Purpose**: 管理临时文件和资源清理

**Interface**:
```python
class ResourceManager:
    def __init__(self, temp_dir: str, keep_files: bool = False):
        self.temp_dir = Path(temp_dir)
        self.keep_files = keep_files
        self.tracked_files: List[Path] = []
    
    def register_file(self, file_path: Path) -> None:
        """注册需要清理的文件"""
        pass
    
    def cleanup(self) -> None:
        """清理所有临时文件"""
        pass
    
    def check_disk_space(self, required_mb: int) -> bool:
        """检查磁盘空间是否充足"""
        pass
```

**Implementation Notes**:
- 使用上下文管理器确保清理
- 即使发生异常也要执行清理
- 记录清理失败但不抛出异常

**Properties**:
- Property 24: cleanup()应是幂等的，多次调用安全
- Property 25: cleanup()后tracked_files中的文件应被删除
- Property 26: 清理失败不应阻止程序继续执行

### 3.9 Logger

**Purpose**: 统一日志管理

**Interface**:
```python
class Logger:
    def __init__(self, name: str, level: str = "INFO", log_file: Optional[Path] = None):
        self.logger = logging.getLogger(name)
        self.level = level
        self.log_file = log_file
    
    def info(self, message: str) -> None:
        pass
    
    def warning(self, message: str) -> None:
        pass
    
    def error(self, message: str, exc_info: bool = False) -> None:
        pass
    
    def debug(self, message: str) -> None:
        pass
```

**Implementation Notes**:
- 使用Python标准logging库
- 同时输出到控制台和文件
- 格式：`[时间] [级别] [模块] 消息`

**Properties**:
- Property 27: 每个处理步骤的开始日志应有对应的结束日志
- Property 28: 所有异常应被记录到日志


## 4. Main Controller

### 4.1 TextExtractor

**Purpose**: 主控制器，协调整个提取流程

**Interface**:
```python
class TextExtractor:
    def __init__(self, config: Config):
        self.config = config
        self.logger = Logger("TextExtractor", config.log_level)
        self.resource_manager = ResourceManager(config.temp_dir, config.keep_temp_files)
        self.subtitle_fetcher = SubtitleFetcher(config)
        self.video_downloader = VideoDownloader(config)
        self.audio_extractor = AudioExtractor()
        self.asr_engine = self._create_asr_engine()
        self.ocr_engine = OCREngine(config) if config.enable_ocr else None
    
    def extract(self, url: str, progress_callback: Optional[Callable] = None) -> ExtractionResult:
        """主提取流程"""
        pass
    
    def extract_batch(self, urls: List[str]) -> List[ExtractionResult]:
        """批量提取"""
        pass
    
    def _create_asr_engine(self) -> ASREngine:
        """根据配置创建ASR引擎"""
        pass
```

**Main Flow**:
```python
def extract(self, url: str, progress_callback: Optional[Callable] = None) -> ExtractionResult:
    try:
        # 1. 验证URL
        if not URLValidator.validate(url):
            raise ValueError(f"Invalid URL: {url}")
        
        video_id = URLValidator.extract_video_id(url)
        self.logger.info(f"Processing video: {video_id}")
        
        # 2. 尝试获取官方字幕
        if self.subtitle_fetcher.check_subtitle_availability(video_id):
            self.logger.info("Official subtitle found, downloading...")
            subtitle_files = self.subtitle_fetcher.download_subtitles(video_id)
            segments = self.subtitle_fetcher.parse_subtitle(subtitle_files[0])
            method = "subtitle"
        else:
            # 3. 下载视频
            self.logger.info("No official subtitle, downloading video...")
            video_path = self.video_downloader.download(video_id, progress_callback)
            self.resource_manager.register_file(video_path)
            
            # 4. 提取音频
            self.logger.info("Extracting audio...")
            audio_path = self.audio_extractor.extract(video_path)
            self.resource_manager.register_file(audio_path)
            
            # 5. ASR识别
            self.logger.info("Running ASR...")
            segments = self.asr_engine.transcribe(audio_path, progress_callback)
            method = "asr"
            
            # 6. 可选OCR
            if self.ocr_engine:
                self.logger.info("Running OCR...")
                ocr_segments = self.ocr_engine.extract_text_from_frames(video_path, None)
                segments = self.ocr_engine.merge_with_asr(ocr_segments, segments)
                method = "hybrid"
        
        # 7. 生成结果
        result = ExtractionResult(
            video_info=VideoInfo(video_id, "", 0, method == "subtitle", url),
            segments=segments,
            method=method,
            processing_time=0,
            metadata={}
        )
        
        return result
    
    finally:
        # 8. 清理资源
        self.resource_manager.cleanup()
```

**Properties**:
- Property 29: 无论成功或失败，cleanup()都应被调用
- Property 30: 批量处理中单个失败不应影响其他视频
- Property 31: 相同URL的多次提取应产生一致的结果


## 5. Error Handling Strategy

### 5.1 Error Types

```python
class BilibiliExtractorError(Exception):
    """基础异常类"""
    pass

class URLValidationError(BilibiliExtractorError):
    """URL验证错误"""
    pass

class SubtitleNotFoundError(BilibiliExtractorError):
    """字幕不存在"""
    pass

class DownloadError(BilibiliExtractorError):
    """下载失败"""
    pass

class ASRError(BilibiliExtractorError):
    """ASR识别失败"""
    pass

class InsufficientDiskSpaceError(BilibiliExtractorError):
    """磁盘空间不足"""
    pass
```

### 5.2 Error Handling Rules

1. **URL验证错误**: 立即返回，不继续处理
2. **字幕下载失败**: 降级到视频下载+ASR
3. **视频下载失败**: 尝试备用工具，全部失败则返回错误
4. **ASR失败**: 返回部分结果和错误信息
5. **OCR失败**: 仅记录警告，不影响主流程
6. **资源清理失败**: 记录日志但不抛出异常

**Properties**:
- Property 32: 所有异常应被捕获并记录
- Property 33: 用户可见的错误消息应清晰且可操作
- Property 34: 系统不应因单个模块失败而完全崩溃

## 6. Performance Optimization

### 6.1 CPU Optimization for ASR

**FunASR Optimization**:
1. 使用INT8量化模型（速度提升2-3倍）
2. 使用ONNX Runtime（速度提升3-4倍）
3. 批处理音频片段
4. 启用VAD减少处理时长

**Implementation**:
```python
# INT8量化
pipeline = AutoModel(
    model="paraformer-zh",
    model_revision="v2.0",
    device="cpu",
    quantize=True  # 启用INT8量化
)

# ONNX Runtime
pipeline = AutoModel(
    model="paraformer-zh-onnx",
    device="cpu"
)
```

### 6.2 Download Optimization

- 使用BBDown的多线程下载
- 选择合适的视频质量（720P平衡质量和速度）
- 使用低码率音频（32kbps）加快ASR

### 6.3 Memory Management

- 流式处理大文件
- 及时释放不需要的资源
- 限制并发处理数量

**Properties**:
- Property 35: INT8量化不应显著降低识别准确率（<5%）
- Property 36: 内存使用应随视频时长线性增长
- Property 37: 处理时间应与视频时长成正比


## 7. Configuration Management

### 7.1 Configuration File Format

**config.yaml**:
```yaml
# 通用配置
temp_dir: "./temp"
output_dir: "./output"
log_level: "INFO"  # DEBUG/INFO/WARNING/ERROR
keep_temp_files: false

# 下载配置
download:
  cookie_file: null  # 可选，用于访问大会员内容
  video_quality: "720P"  # 480P/720P/1080P
  threads: 4

# ASR配置
asr:
  engine: "funasr"  # funasr/whisper
  funasr:
    model: "paraformer-zh"
    use_int8: true
    use_onnx: false
  whisper:
    model: "base"  # tiny/base/small/medium/large
    language: null  # 自动检测

# OCR配置
ocr:
  enabled: false
  engine: "paddleocr"  # paddleocr/tesseract

# 输出配置
output:
  format: "srt"  # srt/json/txt/markdown
  include_metadata: true
```

### 7.2 Configuration Loading

```python
class ConfigLoader:
    @staticmethod
    def load_from_file(config_path: Path) -> Config:
        """从YAML文件加载配置"""
        pass
    
    @staticmethod
    def load_from_args(args: argparse.Namespace) -> Config:
        """从命令行参数加载配置"""
        pass
    
    @staticmethod
    def merge_configs(file_config: Config, args_config: Config) -> Config:
        """合并配置，命令行参数优先"""
        pass
    
    @staticmethod
    def validate_config(config: Config) -> bool:
        """验证配置有效性"""
        pass
```

**Properties**:
- Property 38: 配置验证应拒绝无效值
- Property 39: 命令行参数应覆盖配置文件
- Property 40: 缺失的配置项应使用默认值


## 8. CLI Interface

### 8.1 Command Structure

```bash
# 基本用法
bilibili-extractor <url> [options]

# 批量处理
bilibili-extractor --batch urls.txt [options]

# 使用配置文件
bilibili-extractor <url> --config config.yaml [options]
```

### 8.2 CLI Arguments

```python
parser = argparse.ArgumentParser(description="Extract text from Bilibili videos")

# 位置参数
parser.add_argument("url", nargs="?", help="Bilibili video URL")

# 输入选项
parser.add_argument("--batch", type=str, help="File containing list of URLs")

# 配置选项
parser.add_argument("--config", type=str, help="Path to config file")
parser.add_argument("--cookie", type=str, help="Path to cookie file")

# ASR选项
parser.add_argument("--asr-engine", choices=["funasr", "whisper"], default="funasr")
parser.add_argument("--whisper-model", choices=["tiny", "base", "small", "medium", "large"])
parser.add_argument("--language", type=str, help="Language code (for Whisper)")

# 输出选项
parser.add_argument("--output", "-o", type=str, help="Output file path")
parser.add_argument("--format", "-f", choices=["srt", "json", "txt", "markdown"], default="srt")
parser.add_argument("--output-dir", type=str, default="./output")

# 其他选项
parser.add_argument("--keep-temp", action="store_true", help="Keep temporary files")
parser.add_argument("--enable-ocr", action="store_true", help="Enable OCR for hard subtitles")
parser.add_argument("--log-level", choices=["DEBUG", "INFO", "WARNING", "ERROR"], default="INFO")
parser.add_argument("--version", action="version", version="%(prog)s 1.0.0")
```

### 8.3 CLI Output

**Progress Display**:
```
[INFO] Processing video: BV1xx411c7mD
[INFO] Checking for official subtitles...
[INFO] No official subtitle found
[INFO] Downloading video... [████████████████████] 100% (45.2 MB/45.2 MB)
[INFO] Extracting audio...
[INFO] Running ASR... [████████████░░░░░░░░] 65% (ETA: 2m 15s)
```

**Summary Report**:
```
=== Extraction Complete ===
Video ID: BV1xx411c7mD
Method: ASR (FunASR)
Duration: 15m 32s
Segments: 234
Processing Time: 3m 45s
Output: ./output/BV1xx411c7mD.srt
```

**Properties**:
- Property 41: CLI应返回适当的退出码（0=成功，非0=失败）
- Property 42: 进度显示应实时更新
- Property 43: 错误消息应包含可操作的建议


## 9. Testing Strategy

### 9.1 Unit Tests

**Coverage Areas**:
- URLValidator: 各种URL格式的验证和解析
- SubtitleFetcher: 字幕文件解析（SRT/JSON/XML）
- AudioExtractor: 音频提取和验证
- OutputFormatter: 各种格式的输出和验证
- ConfigLoader: 配置加载和验证

### 9.2 Integration Tests

**Test Scenarios**:
1. 完整流程：URL → 官方字幕 → 输出
2. 完整流程：URL → 视频下载 → ASR → 输出
3. 批量处理多个视频
4. 错误恢复：下载失败后使用备用工具
5. 资源清理：异常情况下的清理

### 9.3 Property-Based Tests

**Key Properties to Test**:
- 时间戳单调性和范围验证
- 格式转换的往返一致性
- 幂等性操作
- 错误处理的完整性

### 9.4 Performance Tests

**Benchmarks**:
- ASR处理速度（标准模型 vs INT8 vs ONNX）
- 内存使用随视频时长的增长
- 批量处理的吞吐量

## 10. Dependencies

### 10.1 External Tools

- **BBDown**: B站视频下载（需要单独安装）
- **FFmpeg**: 音频提取（需要单独安装）

### 10.2 Python Libraries

**Core Dependencies**:
```
funasr>=1.0.0          # FunASR语音识别
openai-whisper>=20230314  # Whisper备用引擎
ffmpeg-python>=0.2.0   # FFmpeg Python接口
requests>=2.31.0       # HTTP请求
pyyaml>=6.0           # 配置文件解析
```

**Optional Dependencies**:
```
paddleocr>=2.7.0      # OCR功能
opencv-python>=4.8.0  # 视频帧处理
```

**Development Dependencies**:
```
pytest>=7.4.0         # 测试框架
pytest-cov>=4.1.0     # 测试覆盖率
hypothesis>=6.82.0    # 属性测试
black>=23.7.0         # 代码格式化
mypy>=1.4.0          # 类型检查
```

### 10.3 Installation

```bash
# 基础安装
pip install bilibili-extractor

# 包含OCR功能
pip install bilibili-extractor[ocr]

# 开发环境
pip install bilibili-extractor[dev]
```


## 11. Project Structure

```
bilibili-extractor/
├── src/
│   └── bilibili_extractor/
│       ├── __init__.py
│       ├── __main__.py           # CLI入口
│       ├── core/
│       │   ├── __init__.py
│       │   ├── extractor.py      # TextExtractor主控制器
│       │   ├── models.py         # 数据模型
│       │   └── config.py         # Config和ConfigLoader
│       ├── modules/
│       │   ├── __init__.py
│       │   ├── url_validator.py  # URL验证
│       │   ├── subtitle_fetcher.py
│       │   ├── video_downloader.py
│       │   ├── audio_extractor.py
│       │   ├── asr_engine.py     # ASR引擎抽象和实现
│       │   ├── ocr_engine.py
│       │   └── output_formatter.py
│       ├── utils/
│       │   ├── __init__.py
│       │   ├── logger.py
│       │   ├── resource_manager.py
│       │   └── progress.py       # 进度显示
│       └── cli.py                # CLI参数解析
├── tests/
│   ├── unit/
│   │   ├── test_url_validator.py
│   │   ├── test_subtitle_fetcher.py
│   │   ├── test_audio_extractor.py
│   │   ├── test_output_formatter.py
│   │   └── test_config.py
│   ├── integration/
│   │   ├── test_full_workflow.py
│   │   └── test_batch_processing.py
│   ├── property/
│   │   ├── test_timestamp_properties.py
│   │   ├── test_format_properties.py
│   │   └── test_idempotence.py
│   └── fixtures/
│       ├── sample_subtitles/
│       └── sample_audio/
├── config/
│   └── default_config.yaml
├── docs/
│   ├── README.md
│   ├── installation.md
│   ├── usage.md
│   └── api.md
├── pyproject.toml
├── setup.py
├── requirements.txt
├── requirements-dev.txt
└── README.md
```

## 12. Correctness Properties Summary

### Validation Properties (1-2)
1. URL提取的video_id一致性
2. validate()与extract_video_id()的一致性

### Timestamp Properties (3-4, 9, 12-13, 17-18)
3. 字幕时间戳单调递增
4. start_time < end_time
9. 音频时长与视频时长一致
12. ASR时间戳单调递增
13. 时间戳在有效范围内
17. OCR时间戳对应帧时间
18. 合并后时间戳单调递增

### Round Trip Properties (5, 10, 20-23)
5. SRT解析后重新生成保持一致
10. 音频文件可被标准库读取
20. SRT输出可被解析器解析
21. JSON输出符合schema
22. 格式转换保持时间戳
23. 重新解析得到等价结构

### Idempotence Properties (6, 24, 31)
6. 同一视频多次下载内容一致
24. cleanup()幂等性
31. 同一URL多次提取结果一致

### Error Handling Properties (7-8, 11, 16, 19, 26-28, 32-34)
7. 下载的视频可被ffmpeg读取
8. 下载进度单调递增
11. 损坏视频返回明确错误
16. 空音频返回空列表
19. 无字幕帧不产生OCR结果
26. 清理失败不阻止执行
27. 每个步骤有开始和结束日志
28. 所有异常被记录
32. 所有异常被捕获和记录
33. 错误消息清晰可操作
34. 单个模块失败不导致崩溃

### Performance Properties (14-15, 35-37)
14. FunASR准确率高于Whisper
15. 识别进度单调递增
35. INT8量化准确率下降<5%
36. 内存使用线性增长
37. 处理时间与视频时长成正比

### Configuration Properties (38-40)
38. 配置验证拒绝无效值
39. 命令行参数覆盖配置文件
40. 缺失配置使用默认值

### Batch Processing Properties (30)
30. 批量处理单个失败不影响其他

### CLI Properties (41-43)
41. 适当的退出码
42. 进度实时更新
43. 错误消息包含建议

### Confluence Properties (18)
18. OCR和ASR合并顺序不影响时间戳顺序

### Resource Management Properties (25, 29)
25. cleanup()后文件被删除
29. 无论成功失败都执行cleanup()

## 13. Implementation Phases

### Phase 1: MVP Core (官方字幕提取)
- URL验证和视频信息提取
- BBDown集成（字幕下载）
- 字幕格式解析
- 基础输出格式（SRT）
- 配置管理
- 日志系统

### Phase 2: ASR Integration
- BBDown视频下载
- FFmpeg音频提取
- FunASR集成
- 进度反馈
- 资源清理

### Phase 3: CPU Optimization
- INT8量化支持
- ONNX Runtime集成
- 性能测试和调优

### Phase 4: Extended Features
- Whisper备用引擎
- 多格式输出（JSON/TXT/Markdown）
- 批量处理
- OCR功能（可选）

### Phase 5: Polish
- CLI完善
- 错误处理优化
- 文档完善
- 完整测试套件

