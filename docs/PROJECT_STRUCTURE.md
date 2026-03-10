# 项目目录结构说明

本文档详细说明了 Bilibili Video Text Extractor 项目的目录结构和组织方式。

## 📁 顶层目录结构

```
D:\Kiro_proj\Test1/
├── .kiro/              # Kiro AI 助手相关文件
├── src/                # 项目源代码
├── tests/              # 测试代码
├── config/             # 配置文件
├── tools/              # 外部工具
├── docs/               # 文档
├── output/             # 输出目录
├── temp/               # 临时文件
└── [配置文件]          # 项目级配置
```

## 🤖 .kiro/ - Kiro AI 相关文件

```
.kiro/
├── specs/              # 功能规范文档
│   ├── bilibili-video-text-extractor/    # 主项目规范
│   └── ai-subtitle-and-cookie-management/ # AI字幕和Cookie管理规范
└── steering/           # 开发指南和规则
    ├── product.md      # 产品概述
    ├── structure.md    # 项目结构指南
    └── tech.md         # 技术栈说明
```

**用途**：
- Kiro AI 助手使用的规范和指南
- 不应手动修改，由Kiro管理
- 包含功能需求、设计文档和任务列表

## 💻 src/ - 项目源代码

```
src/
└── bilibili_extractor/
    ├── __init__.py
    ├── __main__.py         # CLI入口点
    ├── cli.py              # 命令行接口
    │
    ├── core/               # 核心业务逻辑
    │   ├── config.py       # 配置管理
    │   ├── extractor.py    # 主提取器
    │   ├── models.py       # 数据模型
    │   └── exceptions.py   # 异常定义
    │
    ├── modules/            # 功能模块
    │   ├── auth_manager.py     # Cookie和登录管理
    │   ├── bilibili_api.py     # Bilibili API客户端
    │   ├── wbi_sign.py         # WBI签名算法
    │   ├── subtitle_parser.py  # 字幕解析
    │   ├── url_validator.py    # URL验证
    │   ├── subtitle_fetcher.py # 字幕下载
    │   ├── video_downloader.py # 视频下载
    │   ├── audio_extractor.py  # 音频提取
    │   ├── asr_engine.py       # ASR引擎
    │   └── output_formatter.py # 输出格式化
    │
    └── utils/              # 工具函数
        ├── logger.py       # 日志系统
        ├── resource_manager.py  # 资源管理
        └── validators.py   # 验证工具
```

**用途**：
- 所有Python源代码
- 按功能模块组织
- 遵循单一职责原则

## 🧪 tests/ - 测试代码

```
tests/
├── unit/               # 单元测试（154个测试）
│   ├── test_auth_manager.py
│   ├── test_bilibili_api.py
│   ├── test_subtitle_parser.py
│   └── ...
├── integration/        # 集成测试
├── property/           # 属性测试
├── fixtures/           # 测试数据
└── test_core_functionality.py  # 核心功能测试
```

**用途**：
- 所有测试代码
- 使用pytest框架
- 运行：`pytest tests/`

## ⚙️ config/ - 配置文件

```
config/
├── default_config.yaml     # 默认配置
├── example_config.yaml     # 示例配置（模板）
└── config.yaml             # 用户配置（不提交到Git）
```

**用途**：
- 存放YAML配置文件
- `example_config.yaml` 是模板，复制后修改
- `config.yaml` 是实际使用的配置（被.gitignore忽略）

**使用方法**：
```bash
# 复制示例配置
cp config/example_config.yaml config/config.yaml

# 编辑配置
vim config/config.yaml

# 使用配置
python -m bilibili_extractor "视频URL" --config config/config.yaml
```

## 🔧 tools/ - 外部工具

```
tools/
├── BBDown/             # BBDown工具目录
│   ├── BBDown.exe      # BBDown可执行文件
│   ├── BBDown.data     # Cookie文件（登录后生成）
│   └── qrcode.png      # 登录二维码（临时）
│
└── ffmpeg/             # FFmpeg工具目录
    ├── bin/            # 可执行文件
    │   ├── ffmpeg.exe
    │   └── ffprobe.exe
    ├── doc/            # 文档
    └── presets/        # 预设
```

**用途**：
- 存放外部依赖工具
- BBDown：B站视频下载
- FFmpeg：音视频处理

**安装方法**：
1. 下载BBDown.exe，放到 `tools/BBDown/`
2. 下载FFmpeg，解压到 `tools/ffmpeg/`
3. 系统会自动检测这些工具

**环境变量**（可选）：
```bash
# 指定BBDown目录
export BBDOWN_DIR="D:/Kiro_proj/Test1/tools/BBDown"
```

## 📚 docs/ - 文档

```
docs/
├── PROJECT_STRUCTURE.md        # 本文件
├── AI_SUBTITLE_ANALYSIS.md     # AI字幕分析
├── SUBBATCH_LOGIC_ANALYSIS.md  # SubBatch逻辑分析
├── COOKIE_GUIDE.md             # Cookie使用指南
└── test_cookie_usage.md        # Cookie测试文档
```

**用途**：
- 项目文档和分析报告
- 技术调研文档
- 使用指南

## 📤 output/ - 输出目录

```
output/
├── BV1xx411c7mD.srt    # 提取的字幕文件
├── BV1yy411c7mE.json   # JSON格式输出
└── ...
```

**用途**：
- 默认输出目录
- 存放提取的字幕文件
- 可通过 `--output-dir` 参数修改

## 🗑️ temp/ - 临时文件

```
temp/
├── BV1xx411c7mD.mp4    # 下载的视频（临时）
├── BV1xx411c7mD.wav    # 提取的音频（临时）
└── ...
```

**用途**：
- 存放处理过程中的临时文件
- 默认会自动清理
- 使用 `--keep-temp` 保留临时文件

## 📄 项目配置文件

```
根目录/
├── README.md               # 项目说明
├── pyproject.toml          # Python项目配置
├── setup.py                # 安装脚本
├── requirements.txt        # 核心依赖
├── requirements-dev.txt    # 开发依赖
├── .gitignore              # Git忽略规则
├── LICENSE                 # 许可证
└── CHANGELOG.md            # 更新日志
```

## 🔍 文件查找优先级

### Cookie文件查找顺序：
1. 环境变量 `BBDOWN_DIR` 指定的目录
2. `项目根目录/tools/BBDown/BBDown.data`
3. 向上查找3层的 `tools/BBDown/BBDown.data`
4. BBDown.exe所在目录（通过PATH查找）
5. 当前工作目录
6. 系统常见位置

### BBDown可执行文件查找顺序：
1. 配置文件中的 `bbdown_path`
2. `项目根目录/tools/BBDown/BBDown.exe`
3. 向上查找3层的 `tools/BBDown/BBDown.exe`
4. 系统PATH

### 配置文件加载顺序：
1. 命令行参数（最高优先级）
2. `--config` 指定的配置文件
3. `config/default_config.yaml`
4. 内置默认值

## 🚫 .gitignore 规则

以下文件/目录不会提交到Git：

```
# 临时和输出
temp/
output/
*.log

# Cookie和敏感信息
tools/BBDown/BBDown.data
tools/BBDown/qrcode.png

# 用户配置
config/config.yaml

# Python缓存
__pycache__/
*.pyc
.pytest_cache/

# IDE
.vscode/
.idea/
```

## 📝 最佳实践

### 1. 工具安装
- ✅ 推荐：将工具放在 `tools/` 目录
- ⚠️ 备选：添加到系统PATH

### 2. 配置管理
- ✅ 复制 `example_config.yaml` 为 `config.yaml`
- ✅ 在 `config.yaml` 中修改个人配置
- ❌ 不要直接修改 `example_config.yaml`

### 3. Cookie管理
- ✅ 使用 `--login` 登录，Cookie自动保存
- ✅ Cookie文件会自动检测
- ⚠️ 不要手动编辑Cookie文件

### 4. 开发流程
- ✅ 在 `src/` 中编写代码
- ✅ 在 `tests/` 中编写测试
- ✅ 运行 `pytest` 验证
- ✅ 更新文档

## 🔄 目录维护

### 清理临时文件
```bash
# 清理temp目录
rm -rf temp/*

# 清理output目录
rm -rf output/*

# 清理Python缓存
find . -type d -name __pycache__ -exec rm -rf {} +
```

### 重置项目
```bash
# 清理所有生成的文件
rm -rf temp/ output/ .pytest_cache/
rm -rf src/*.egg-info/
find . -type d -name __pycache__ -exec rm -rf {} +
```

## 📞 相关命令

```bash
# 查看项目结构
tree -L 3 -I '__pycache__|*.pyc|.pytest_cache'

# 检查Cookie状态
python -m bilibili_extractor --check-cookie

# 查看配置
cat config/config.yaml

# 运行测试
pytest tests/ -v

# 安装项目
pip install -e .
```
