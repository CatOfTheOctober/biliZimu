# 安装和配置指南

本指南详细说明如何安装和配置 Bilibili Video Text Extractor，确保其他用户下载后可以直接使用。

## 📋 前置要求

- Python 3.8 或更高版本
- pip 包管理器
- Git（用于克隆项目）

## 🚀 快速开始

### 1. 克隆项目

```bash
git clone <repository-url>
cd bilibili-extractor
```

### 2. 安装Python包

```bash
# 安装核心包（开发模式）
pip install -e .

# 可选：安装ASR支持
pip install funasr  # 中文优化
# 或
pip install openai-whisper  # 多语言支持
```

### 3. 下载外部工具

#### 方式A：使用项目内置目录（推荐）

**优点**：
- 无需配置PATH
- 项目自包含，易于分发
- 自动检测工具位置

**步骤**：

1. **下载BBDown**
   - 访问：https://github.com/nilaoda/BBDown/releases
   - 下载最新版本的 `BBDown.exe`
   - 放置到：`tools/BBDown/BBDown.exe`

2. **下载FFmpeg**
   - 访问：https://ffmpeg.org/download.html
   - 下载Windows版本（full build）
   - 解压到：`tools/ffmpeg/`
   - 确保结构为：
     ```
     tools/ffmpeg/
     ├── bin/
     │   ├── ffmpeg.exe
     │   └── ffprobe.exe
     ├── doc/
     └── presets/
     ```

**目录结构**：
```
bilibili-extractor/
├── tools/
│   ├── BBDown/
│   │   └── BBDown.exe          # 放这里
│   └── ffmpeg/
│       └── bin/
│           ├── ffmpeg.exe      # 放这里
│           └── ffprobe.exe     # 放这里
├── src/
├── config/
└── ...
```

#### 方式B：添加到系统PATH

如果你已经在系统中安装了这些工具，可以跳过下载步骤。

### 4. 验证安装

```bash
# 检查Python包
python -m bilibili_extractor --version

# 检查Cookie状态（会自动检测工具）
python -m bilibili_extractor --check-cookie
```

## 🔧 详细配置

### 工具路径自动检测

系统会按以下顺序自动查找工具：

#### BBDown查找顺序：
1. 配置文件中的 `bbdown_path`
2. **`项目根目录/tools/BBDown/BBDown.exe`** ⭐ 推荐
3. 环境变量 `BBDOWN_DIR`
4. 系统PATH

#### FFmpeg查找顺序：
1. 配置文件中的 `ffmpeg_path`
2. **`项目根目录/tools/ffmpeg/bin/ffmpeg.exe`** ⭐ 推荐
3. 系统PATH

### Cookie文件自动检测

Cookie文件查找顺序：
1. 配置文件中的 `cookie_file`
2. **`项目根目录/tools/BBDown/BBDown.data`** ⭐ 推荐
3. BBDown.exe所在目录
4. 当前工作目录

### 使用配置文件（可选）

如果需要自定义配置：

```bash
# 1. 复制配置模板
cp config/example_config.yaml config/config.yaml

# 2. 编辑配置（可选）
vim config/config.yaml

# 3. 使用配置
python -m bilibili_extractor "视频URL" --config config/config.yaml
```

**配置文件示例**（支持相对路径）：
```yaml
# 工具路径（相对于项目根目录）
bbdown_path: "tools/BBDown/BBDown.exe"
ffmpeg_path: "tools/ffmpeg/bin/ffmpeg.exe"
cookie_file: "tools/BBDown/BBDown.data"

# 输出配置
output_dir: "./output"
output_format: "srt"
```

## 🔐 Cookie管理

### 登录B站账号

```bash
# 使用BBDown登录（扫码）
python -m bilibili_extractor --login
```

登录后，Cookie会自动保存到 `tools/BBDown/BBDown.data`

### 检查Cookie状态

```bash
python -m bilibili_extractor --check-cookie
```

输出示例：
```
==================================================
=== Cookie Status Check ===
==================================================
Cookie file: D:\project\tools\BBDown\BBDown.data
Status: ✓ Found
Format: ✓ Valid
SESSDATA: 9ec450a1,1... (hidden)

✓ Cookie is valid and ready to use
==================================================
```

## 📦 分发给其他用户

### 方式1：完整打包（推荐）

将整个项目文件夹打包，包含：
- 源代码
- tools目录（包含BBDown和FFmpeg）
- 配置文件

**优点**：
- 用户解压即用
- 无需额外下载工具
- 无需配置PATH

**步骤**：
```bash
# 1. 确保tools目录包含所有工具
ls tools/BBDown/BBDown.exe
ls tools/ffmpeg/bin/ffmpeg.exe

# 2. 打包（排除敏感文件）
# 注意：不要包含 BBDown.data（Cookie文件）
zip -r bilibili-extractor.zip . -x "*.pyc" "__pycache__/*" ".git/*" "tools/BBDown/BBDown.data"

# 3. 分发给用户
```

**用户使用**：
```bash
# 1. 解压
unzip bilibili-extractor.zip
cd bilibili-extractor

# 2. 安装Python依赖
pip install -e .

# 3. 登录（首次使用）
python -m bilibili_extractor --login

# 4. 开始使用
python -m bilibili_extractor "视频URL"
```

### 方式2：仅源代码

如果不想包含大文件（FFmpeg约100MB），可以只分发源代码：

```bash
# 1. 创建安装说明
cat > INSTALL.txt << EOF
安装步骤：
1. pip install -e .
2. 下载BBDown到 tools/BBDown/
3. 下载FFmpeg到 tools/ffmpeg/
4. python -m bilibili_extractor --login
EOF

# 2. 打包源代码
zip -r bilibili-extractor-src.zip . -x "tools/*" "*.pyc" "__pycache__/*" ".git/*"
```

## 🐛 常见问题

### 1. 找不到BBDown

**错误信息**：
```
BBDown not found. Please:
1. Place BBDown.exe in tools/BBDown/ directory, or
2. Add BBDown to system PATH, or
3. Set bbdown_path in config file
```

**解决方案**：
```bash
# 检查文件是否存在
ls tools/BBDown/BBDown.exe

# 如果不存在，下载并放置
# 下载地址：https://github.com/nilaoda/BBDown/releases
```

### 2. 找不到FFmpeg

**解决方案**：
```bash
# 检查文件是否存在
ls tools/ffmpeg/bin/ffmpeg.exe

# 如果不存在，下载并解压
# 下载地址：https://ffmpeg.org/download.html
```

### 3. Cookie文件未找到

**解决方案**：
```bash
# 首次使用需要登录
python -m bilibili_extractor --login

# 登录后Cookie会自动保存到 tools/BBDown/BBDown.data
```

### 4. 相对路径不工作

**原因**：可能不在项目根目录运行

**解决方案**：
```bash
# 确保在项目根目录
cd /path/to/bilibili-extractor

# 或使用绝对路径配置
# 在 config/config.yaml 中：
bbdown_path: "D:/path/to/tools/BBDown/BBDown.exe"
```

## 🔄 更新工具

### 更新BBDown

```bash
# 1. 下载新版本
# 2. 替换 tools/BBDown/BBDown.exe
# 3. Cookie文件会保留
```

### 更新FFmpeg

```bash
# 1. 下载新版本
# 2. 解压并替换 tools/ffmpeg/ 目录
```

## 📝 环境变量（可选）

如果需要在多个项目间共享工具：

```bash
# Windows PowerShell
$env:BBDOWN_DIR = "D:\Tools\BBDown"

# 或永久设置（系统环境变量）
# 控制面板 → 系统 → 高级系统设置 → 环境变量
# 新建：BBDOWN_DIR = D:\Tools\BBDown
```

## ✅ 验证清单

安装完成后，检查以下项目：

- [ ] Python包已安装：`pip list | grep bilibili-extractor`
- [ ] BBDown存在：`ls tools/BBDown/BBDown.exe`
- [ ] FFmpeg存在：`ls tools/ffmpeg/bin/ffmpeg.exe`
- [ ] Cookie检测正常：`python -m bilibili_extractor --check-cookie`
- [ ] 可以提取字幕：`python -m bilibili_extractor "测试URL"`

## 📚 相关文档

- [项目结构说明](PROJECT_STRUCTURE.md)
- [SubBatch参考说明](SUBBATCH_REFERENCE.md)
- [Cookie使用指南](COOKIE_GUIDE.md)
- [配置文件示例](../config/example_config.yaml)
- [README](../README.md)
