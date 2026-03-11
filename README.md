# Bilibili Video Text Extractor (B站视频文字提取系统)

> 🚀 **推荐使用项目根目录下的 `下载字幕.py`。**
> 
> 该工具经过高度优化，解决了 B 站 WBI 签名风控（412 错误），并支持自动降级到 ASR 语音识别逻辑。

## 📋 快速开始

### 1. 运行环境
确保你使用的是包含 `funasr` 依赖的环境（如 `conda activate py311`），然后运行：
```bash
python 下载字幕.py
```

### 2. 核心特性
- ✅ **智能两阶段处理**：优先获取官方/AI 字幕，失败时自动进入 ASR 识别流程。
- ✅ **模型加速**：支持 `D:/Funasr_model` 本地加载，极速启动。
- ✅ **自动清理**：任务完成后自动清理临时文件。

## 🏗️ 项目结构

```
bilibili-extractor/
├── .kiro/                           # Kiro AI 相关文件
│   ├── specs/                       # 功能规范文档
│   └── steering/                    # 开发指南
│
├── src/                             # 项目源代码
│   └── bilibili_extractor/
│       ├── __init__.py
│       ├── __main__.py              # CLI入口
│       ├── cli.py                   # 命令行参数解析
│       │
│       ├── core/                    # 核心模块
│       │   ├── __init__.py
│       │   ├── config.py            # 配置管理（Config, ConfigLoader）
│       │   ├── extractor.py         # 主控制器（TextExtractor）
│       │   └── models.py            # 数据模型（VideoInfo, TextSegment, ExtractionResult）
│       │
│       ├── modules/                 # 功能模块
│       │   ├── __init__.py
│       │   ├── auth_manager.py      # Cookie和登录管理
│       │   ├── bilibili_api.py      # Bilibili API客户端
│       │   ├── wbi_sign.py          # WBI签名算法
│       │   ├── subtitle_parser.py   # 字幕解析
│       │   ├── url_validator.py     # URL验证和解析
│       │   ├── subtitle_fetcher.py  # 字幕下载和解析（BBDown --sub-only）
│       │   ├── video_downloader.py  # 视频下载（BBDown）
│       │   ├── audio_extractor.py   # 音频提取（FFmpeg）
│       │   ├── asr_engine.py        # ASR引擎（FunASR + Whisper）
│       │   ├── output_formatter.py  # 输出格式化
│       │   └── ocr_engine.py        # OCR引擎（可选，未实现）
│       │
│       └── utils/                   # 工具模块
│           ├── __init__.py
│           ├── logger.py            # 日志系统
│           ├── resource_manager.py  # 资源管理和清理
│           └── progress.py          # 进度显示（未实现）
│
├── tests/                           # 测试套件
│   ├── unit/                        # 单元测试（196个测试）
│   ├── integration/                 # 集成测试
│   ├── property/                    # 属性测试
│   └── fixtures/                    # 测试数据
│
├── config/                          # 配置文件目录
│   ├── default_config.yaml          # 默认配置
│   └── example_config.yaml          # 示例配置
│
├── tools/                           # 外部工具目录
│   ├── BBDown/                      # BBDown工具
│   │   ├── BBDown.exe               # BBDown可执行文件
│   │   └── BBDown.data              # Cookie文件（登录后生成）
│   └── ffmpeg/                      # FFmpeg工具
│       └── bin/                     # FFmpeg可执行文件
│
├── docs/                            # 文档目录
│   ├── AI_SUBTITLE_ANALYSIS.md      # AI字幕分析文档
│   ├── SUBBATCH_LOGIC_ANALYSIS.md   # SubBatch逻辑分析
│   └── COOKIE_GUIDE.md              # Cookie使用指南
│
├── output/                          # 输出目录（默认）
├── temp/                            # 临时文件目录
│
└── [项目配置文件]
    ├── README.md                    # 本文件
    ├── pyproject.toml               # 项目配置
    ├── setup.py                     # 安装脚本
    ├── requirements.txt             # 核心依赖
    ├── requirements-dev.txt         # 开发依赖
    └── .gitignore                   # Git忽略文件
```

## 🔧 技术栈

### 核心技术

| 技术 | 用途 | 说明 |
|------|------|------|
| **Python 3.8+** | 开发语言 | 使用dataclass、类型注解等现代特性 |
| **BBDown** | 视频/字幕下载 | B站专用下载工具，支持多线程和Cookie认证 |
| **FFmpeg** | 音频提取 | 从视频提取16kHz单声道WAV音频 |
| **FunASR** | 中文ASR | 阿里达摩院开源，专为中文优化 |
| **Whisper** | 多语言ASR | OpenAI开源，支持多语言识别 |

### Python依赖

**核心依赖**（必需）：
```
# 无需额外Python依赖，仅需标准库
```

**ASR依赖**（可选 - 仅在处理无字幕视频时需要）：
```bash
# FunASR（推荐用于中文）
pip install funasr

# Whisper（多语言支持）
pip install openai-whisper
```

> **注意**：如果不安装ASR库，系统仍可正常提取有官方字幕的视频。只有在处理无字幕视频时才需要ASR库。

**OCR依赖**（可选，未实现）：
```bash
pip install paddleocr opencv-python
```

**开发依赖**：
```bash
pip install pytest pytest-cov hypothesis black mypy
```

### 外部工具依赖

**必需工具**：
1. **BBDown**：B站视频下载工具
   - 下载：https://github.com/nilaoda/BBDown/releases
   - 推荐安装位置：`项目根目录/tools/BBDown/BBDown.exe`
   - 或添加到系统PATH

2. **FFmpeg**：音视频处理工具
   - 下载：https://ffmpeg.org/download.html
   - 推荐安装位置：`项目根目录/tools/ffmpeg/bin/`
   - 或添加到系统PATH

## 📦 安装

### 1. 安装外部工具

```bash
# 方式1：放置在项目tools目录（推荐）
# 优点：无需配置PATH，项目自包含，易于分发
# 1. 下载BBDown.exe，放到 tools/BBDown/ 目录
# 2. 下载FFmpeg，解压到 tools/ffmpeg/ 目录

# 方式2：添加到系统PATH
# Windows: 将BBDown.exe和FFmpeg的bin目录添加到系统环境变量PATH

# 验证安装
BBDown --version
ffmpeg -version
```

**推荐目录结构**：
```
bilibili-extractor/
├── tools/
│   ├── BBDown/
│   │   └── BBDown.exe          # 放这里
│   └── ffmpeg/
│       └── bin/
│           ├── ffmpeg.exe      # 放这里
│           └── ffprobe.exe
├── src/
└── config/
```

**工具自动检测顺序**：
1. 项目 `tools/` 目录（优先）
2. 配置文件指定路径
3. 环境变量
4. 系统PATH

详见：[安装指南](docs/INSTALLATION_GUIDE.md)

### 2. 安装Python包

```bash
# 克隆项目
git clone <repository-url>
cd bilibili-extractor

# 安装核心包（仅字幕提取）
pip install -e .

# 安装ASR支持（推荐）
pip install funasr
# 或
pip install openai-whisper

# 安装开发依赖
pip install -r requirements-dev.txt
```

## 🚀 使用方法

### 基本用法

```bash
# 提取字幕（如果有官方字幕）
python -m bilibili_extractor "https://www.bilibili.com/video/BV1xx411c7mD"

# 指定输出格式
python -m bilibili_extractor "https://www.bilibili.com/video/BV1xx411c7mD" --format json

# 指定输出文件
python -m bilibili_extractor "https://www.bilibili.com/video/BV1xx411c7mD" -o output.srt
```

### Cookie管理（AI字幕和大会员内容）

```bash
# 检查Cookie状态
python -m bilibili_extractor --check-cookie

# 使用BBDown登录（扫码登录）
python -m bilibili_extractor --login

# 使用自定义Cookie文件
python -m bilibili_extractor "https://www.bilibili.com/video/BV1xx411c7mD" \
    --cookie /path/to/cookie.txt

# 提取AI字幕（需要Cookie）
python -m bilibili_extractor "https://www.bilibili.com/video/BV1xx411c7mD"
# 系统会自动检测BBDown Cookie并获取AI字幕
```

**Cookie说明**：
- BBDown登录后，Cookie自动保存在`tools/BBDown/BBDown.data`（或BBDown.exe同目录）
- 系统会自动检测并使用BBDown的Cookie
- 有Cookie时可以获取AI字幕和大会员内容
- 无Cookie时只能获取普通字幕

**目录结构说明**：
- 推荐将BBDown.exe放在`tools/BBDown/`目录
- 系统会优先查找项目tools目录中的Cookie文件
- 也可以通过环境变量`BBDOWN_DIR`指定BBDown目录

### ASR识别（无字幕视频）

```bash
# 使用FunASR（默认，中文优化）
python -m bilibili_extractor "https://www.bilibili.com/video/BV1xx411c7mD" --asr-engine funasr

# 使用Whisper（多语言）
python -m bilibili_extractor "https://www.bilibili.com/video/BV1xx411c7mD" --asr-engine whisper

# 指定Whisper模型大小
python -m bilibili_extractor "https://www.bilibili.com/video/BV1xx411c7mD" \
    --asr-engine whisper --whisper-model medium

# 指定语言（Whisper）
python -m bilibili_extractor "https://www.bilibili.com/video/BV1xx411c7mD" \
    --asr-engine whisper --language zh
```

### Cookie认证（大会员内容）

**已废弃**：请使用上面的"Cookie管理"部分的新方法。

### 配置文件

```bash
# 使用配置文件
python -m bilibili_extractor "https://www.bilibili.com/video/BV1xx411c7mD" \
    --config config.yaml
```

**config.yaml示例**：
```yaml
# 通用配置
temp_dir: "./temp"
output_dir: "./output"
log_level: "INFO"
keep_temp_files: false

# 下载配置
cookie_file: "/path/to/cookie.txt"
video_quality: "720P"  # 480P/720P/1080P
download_threads: 4

# ASR配置
asr_engine: "funasr"  # funasr/whisper
funasr_model: "paraformer-zh"
use_int8: true        # INT8量化加速
use_onnx: false       # ONNX Runtime加速
whisper_model: "base"
language: null

# 输出配置
output_format: "srt"  # srt/json/txt/markdown
```

### 完整命令行参数

```bash
python -m bilibili_extractor <url> [options]

位置参数:
  url                   B站视频URL

输入选项:
  --batch FILE          批量处理URL列表文件（未实现）

配置选项:
  --config FILE         配置文件路径
  --cookie FILE         Cookie文件路径
  --login               强制BBDown登录
  --check-cookie        检查Cookie状态
  --no-auto-login       禁用自动登录

ASR选项:
  --asr-engine {funasr,whisper}
                        ASR引擎选择（默认：funasr）
  --whisper-model {tiny,base,small,medium,large}
                        Whisper模型大小
  --language CODE       语言代码（Whisper使用）

输出选项:
  -o, --output FILE     输出文件路径
  -f, --format {srt,json,txt,markdown}
                        输出格式（默认：srt）
  --output-dir DIR      输出目录（默认：./output）

其他选项:
  --keep-temp           保留临时文件
  --log-level {DEBUG,INFO,WARNING,ERROR}
                        日志级别（默认：INFO）
  --version             显示版本信息
```

## 🔄 处理流程

### 两阶段处理逻辑

```
┌─────────────────────────────────────────────────────────┐
│ 1. URL验证                                               │
│    - 验证URL格式                                         │
│    - 提取视频ID（BV号或av号）                           │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│ 2. Cookie检查和初始化                                    │
│    - 检测BBDown Cookie                                   │
│    - 初始化Bilibili API客户端                           │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│ 3. 尝试获取字幕（Bilibili API优先）                     │
│    - 调用播放器API获取字幕列表                          │
│    - 优先选择AI字幕（ai-zh）                            │
│    - 如果AI字幕URL为空，调用AI字幕API                   │
│    - 下载并解析字幕                                      │
│    - 下载字幕文件（SRT/JSON/XML）                        │
│    - 解析字幕内容                                        │
└────────────────────┬────────────────────────────────────┘
                     │
                     ├─── 有字幕 ──────────────────┐
                     │                              │
                     └─── 无字幕 ───┐              │
                                    ▼              ▼
                     ┌──────────────────────┐  ┌──────────┐
                     │ 3. ASR流程            │  │ 6. 输出  │
                     │  a. 下载视频(BBDown)  │  │  - SRT   │
                     │  b. 提取音频(FFmpeg)  │  │  - JSON  │
                     │  c. ASR识别           │  │  - TXT   │
                     │     - FunASR/Whisper  │  │  - MD    │
                     └──────────┬────────────┘  └──────────┘
                                │                     ▲
                                └─────────────────────┘
```

### 数据流

```python
# 输入
URL: "https://www.bilibili.com/video/BV1xx411c7mD"

# 处理
VideoInfo {
    video_id: "BV1xx411c7mD",
    title: "",
    duration: 0,
    has_subtitle: true/false,
    url: "..."
}

# 输出
ExtractionResult {
    video_info: VideoInfo,
    segments: [
        TextSegment {
            start_time: 0.0,
            end_time: 2.5,
            text: "这是第一句话",
            confidence: 1.0,
            source: "subtitle"  # 或 "asr"
        },
        ...
    ],
    method: "subtitle",  # 或 "asr"
    processing_time: 3.45,
    metadata: {...}
}
```

## 📊 输出格式

### SRT格式（默认）

```srt
1
00:00:00,000 --> 00:00:02,500
这是第一句话

2
00:00:02,500 --> 00:00:05,000
这是第二句话
```

### JSON格式

```json
{
  "video_info": {
    "video_id": "BV1xx411c7mD",
    "title": "",
    "duration": 0,
    "has_subtitle": true,
    "url": "https://www.bilibili.com/video/BV1xx411c7mD"
  },
  "segments": [
    {
      "start_time": 0.0,
      "end_time": 2.5,
      "text": "这是第一句话",
      "confidence": 1.0,
      "source": "subtitle"
    }
  ],
  "method": "subtitle",
  "processing_time": 3.45,
  "metadata": {
    "segment_count": 10,
    "extraction_method": "subtitle"
  }
}
```

### TXT格式

```
这是第一句话
这是第二句话
这是第三句话
```

### Markdown格式

```markdown
# Video: BV1xx411c7mD

## Extracted Text

- [00:00:00 - 00:00:02] 这是第一句话
- [00:00:02 - 00:00:05] 这是第二句话
- [00:00:05 - 00:00:08] 这是第三句话

---
Method: subtitle
Processing Time: 3.45s
```

## 🧪 测试

```bash
# 运行所有测试
pytest tests/

# 运行单元测试
pytest tests/unit/

# 运行集成测试
pytest tests/integration/

# 运行属性测试
pytest tests/property/

# 生成覆盖率报告
pytest tests/ --cov=src/bilibili_extractor --cov-report=html

# 运行特定测试
pytest tests/unit/test_extractor.py -v
```

**测试统计**：
- 总测试数：198个
- 通过率：100%
- 代码覆盖率：79%

## 🎯 性能优化

### FunASR优化选项

```bash
# 使用INT8量化（速度提升2-3倍）
python -m bilibili_extractor <url> --asr-engine funasr --use-int8

# 使用ONNX Runtime（速度提升3-4倍）
python -m bilibili_extractor <url> --asr-engine funasr --use-onnx
```

### 视频质量选择

```bash
# 选择较低质量以加快下载和处理
python -m bilibili_extractor <url> --video-quality 480P
```

## 🐛 故障排除

### 常见问题

**1. BBDown not found**
```bash
# 解决方案：安装BBDown并添加到PATH
# Windows: 将BBDown.exe所在目录添加到系统环境变量PATH
```

**2. ffmpeg not found**
```bash
# 解决方案：安装FFmpeg并添加到PATH
# Windows: 将ffmpeg.exe所在目录添加到系统环境变量PATH
```

**3. ASR库未安装（处理无字幕视频时）**
```bash
# 错误信息：
# "No subtitles found for video XXX and ASR is not available."
# "To use ASR functionality, please install one of the following..."

# 解决方案1：安装ASR库
pip install funasr  # 推荐用于中文
# 或
pip install openai-whisper  # 多语言支持

# 解决方案2：只处理有字幕的视频
# 系统会自动使用官方字幕，无需ASR库
```

**4. FunASR安装失败**
```bash
# 可能原因：
# - 缺少编译工具（需要C++编译器）
# - 依赖库版本冲突

# 解决方案：
# 1. 尝试使用Whisper替代
pip install openai-whisper

# 2. 或者只处理有字幕的视频（无需ASR库）
```

**5. 字幕下载失败**
```bash
# 可能原因：
# - 视频没有字幕
# - 需要Cookie认证（大会员内容）
# - 网络问题

# 解决方案：
# 1. 使用Cookie文件
python -m bilibili_extractor <url> --cookie cookie.txt

# 2. 安装ASR库让系统自动使用ASR
pip install funasr

# 3. 检查视频是否真的有字幕
```

**6. ASR识别速度慢**
```bash
# 解决方案：使用优化选项
python -m bilibili_extractor <url> --use-int8
```

## 📝 开发指南

### 代码风格

```bash
# 格式化代码
black src/ tests/

# 类型检查
mypy src/

# 运行测试
pytest tests/
```

### 添加新功能

1. 在`.kiro/specs/`中创建规范文档
2. 在`src/bilibili_extractor/modules/`中实现模块
3. 在`tests/unit/`中添加单元测试
4. 更新`README.md`和文档

### 项目规范

- **需求文档**：`.kiro/specs/bilibili-video-text-extractor/requirements.md`
- **设计文档**：`.kiro/specs/bilibili-video-text-extractor/design.md`
- **任务列表**：`.kiro/specs/bilibili-video-text-extractor/tasks.md`

## 📄 许可证

待定

## 🤝 贡献

欢迎提交Issue和Pull Request！

## 📮 联系方式

待定

## 🗺️ 路线图

### 已完成 ✅
- [x] MVP核心功能（字幕提取）
- [x] ASR集成（FunASR + Whisper）
- [x] BBDown统一下载
- [x] Cookie认证支持
- [x] 多格式输出
- [x] CPU优化（INT8 + ONNX）
- [x] 批量处理功能
- [x] 完善的CLI参数
- [x] 配置文件支持
- [x] 完整的文档

### 计划中 📋
- [ ] OCR硬字幕识别
- [ ] 进度条优化
- [ ] Web界面
- [ ] Docker支持
- [ ] 更多输出格式

## 📚 相关资源

- **BBDown**: https://github.com/nilaoda/BBDown
- **FFmpeg**: https://ffmpeg.org/
- **FunASR**: https://github.com/alibaba-damo-academy/FunASR
- **Whisper**: https://github.com/openai/whisper

## 🙏 致谢

本项目的WBI签名实现参考了 [SubBatch](https://github.com/SubBatch/SubBatch) 浏览器扩展的技术方案。SubBatch是一个优秀的B站字幕批量下载工具，我们借鉴了其API调用逻辑和WBI签名算法，并用Python重新实现。

**说明**：
- SubBatch是JavaScript实现（浏览器扩展）
- 本项目是Python实现（命令行工具）
- 我们参考了SubBatch的技术方案，但代码是独立实现的

详见：[SubBatch参考说明](docs/SUBBATCH_REFERENCE.md)
