---
inclusion: always
---

# 技术栈与开发规范

## Python 环境要求

- **Python 版本**: 3.8+ (必须)
- **包管理器**: pip
- **构建工具**: setuptools
- **项目配置**: pyproject.toml (主配置文件)

## 核心依赖

### 必需依赖 (无外部依赖的核心功能)
- `requests>=2.31.0`: Bilibili API HTTP 请求
- `pyyaml>=6.0`: YAML 配置文件解析
- `ffmpeg-python>=0.2.0`: FFmpeg 封装库

### 可选依赖
- **ASR 语音识别**: 
  - `funasr>=1.0.0` (推荐用于中文)
  - `openai-whisper>=20230314` (多语言支持)
- **OCR 文字识别**: 
  - `paddleocr>=2.7.0`, `opencv-python>=4.8.0` (未实现)

### 开发依赖
- `pytest>=7.4.0`: 测试框架
- `pytest-cov>=4.1.0`: 覆盖率报告
- `hypothesis>=6.82.0`: 基于属性的测试 (PBT)
- `black>=23.7.0`: 代码格式化
- `mypy>=1.4.0`: 类型检查

### 外部工具
- **BBDown**: B站视频下载器 (`tools/BBDown/`)
- **FFmpeg**: 音视频处理 (`tools/ffmpeg/`)

## 代码规范

### 项目目录结构规则
- **保持根目录整洁**: 不要在根目录创建临时文件、测试文件或输出文件
- **测试文件位置**: 所有测试必须在 `tests/` 或 `test_temp/` 目录下
- **临时文件位置**: 使用 `temp/` 或 `test_temp/` 目录存放临时文件
- **输出文件位置**: 使用 `output/` 目录存放生成的输出文件
- **配置文件位置**: 用户配置文件放在 `config/` 目录

### 格式化
- 使用 `black` 进行代码格式化
- 运行命令: `black src/ tests/`
- 提交前必须格式化代码

### 类型检查
- 使用 `mypy` 进行静态类型检查
- 运行命令: `mypy src/`
- 所有公共 API 必须有类型注解

### 测试要求
- 单元测试覆盖率目标: >80%
- 使用 `pytest` 编写测试
- 使用 `hypothesis` 编写属性测试
- 测试文件命名: `test_*.py`
- 测试位置: `tests/unit/`, `tests/integration/`, `tests/property/`

## 常用命令

### 开发环境设置
```bash
# 开发模式安装
pip install -e .

# 安装 ASR 支持
pip install -e ".[asr]"

# 安装开发依赖
pip install -r requirements-dev.txt
```

### 代码质量检查
```bash
# 格式化代码
black src/ tests/

# 类型检查
mypy src/

# 运行所有测试
pytest tests/

# 生成覆盖率报告
pytest tests/ --cov=src/bilibili_extractor --cov-report=html

# 运行属性测试
pytest tests/property/ -v
```

### 构建与发布
```bash
# 构建包
python -m build

# 从源码安装
pip install .

# 创建分发包
python setup.py sdist bdist_wheel
```

### 应用使用

**推荐方式（安装后使用命令）**：
```bash
# 首先安装项目（开发模式）
pip install -e .

# 然后可以直接使用命令
bilibili-extractor --check-cookie
bilibili-extractor --login
bilibili-extractor "VIDEO_URL"
bilibili-extractor "VIDEO_URL" --config config/config.yaml
```

**备用方式（使用 python -m）**：
```bash
# 检查 Cookie 状态
python -m bilibili_extractor --check-cookie

# 使用 BBDown 登录
python -m bilibili_extractor --login

# 提取字幕
python -m bilibili_extractor "VIDEO_URL"

# 使用配置文件
python -m bilibili_extractor "VIDEO_URL" --config config/config.yaml
```

**注意**：
- 推荐先运行 `pip install -e .` 安装项目，然后使用 `bilibili-extractor` 命令
- 如果未安装，可以使用 `python -m bilibili_extractor` 方式运行
- 不要直接运行 `python bilibili_extractor`，这是错误的用法

## AI 助手指导规则

### 文件创建规则（重要！）
1. **禁止在根目录创建文件**: 除非是项目配置文件（如 README.md, .gitignore 等）
2. **测试文件位置**: 
   - 正式测试: `tests/unit/`, `tests/integration/`, `tests/property/`
   - 临时测试: `test_temp/` (该目录被 Git 忽略)
   - **绝对禁止**: 在根目录创建 `test_*.py` 文件
3. **临时文件位置**: `temp/` 或 `test_temp/` 目录
4. **输出文件位置**: `output/` 目录
5. **源代码位置**: `src/bilibili_extractor/` 目录

### 代码修改时
1. 修改代码后必须运行 `black` 格式化
2. 添加新函数/类时必须添加类型注解
3. 修改核心逻辑时必须更新或添加测试
4. 使用 `getDiagnostics` 检查语法和类型错误

### 添加依赖时
1. 核心功能依赖添加到 `requirements.txt`
2. 开发工具依赖添加到 `requirements-dev.txt`
3. 可选功能依赖添加到 `pyproject.toml` 的 `[project.optional-dependencies]`
4. 更新 `setup.py` 中的依赖列表

### 测试编写时
1. **严禁在项目根目录创建测试文件** - 所有测试文件必须放在 `tests/` 目录下
2. 单元测试放在 `tests/unit/` 目录
3. 集成测试放在 `tests/integration/` 目录
4. 属性测试放在 `tests/property/` 目录
5. 临时测试文件放在 `test_temp/` 目录（该目录被 Git 忽略）
6. 使用 `hypothesis` 编写属性测试以验证正确性属性
7. 测试文件命名格式: `test_*.py`
8. 测试命名清晰描述测试场景

### 外部工具使用
1. BBDown 位于 `tools/BBDown/BBDown.exe`
2. FFmpeg 位于 `tools/ffmpeg/`
3. 优先使用项目内工具，其次使用系统 PATH
4. Cookie 文件位于 `tools/BBDown/cookie.txt`

## 配置文件管理

- `config/example_config.yaml`: 配置模板 (提交到 Git)
- `config/config.yaml`: 用户配置 (Git 忽略)
- `config/default_config.yaml`: 默认值
- 优先级: CLI 参数 > 配置文件 > 默认值

## 依赖版本管理

### requirements.txt (核心依赖)
```
ffmpeg-python>=0.2.0
requests>=2.31.0
pyyaml>=6.0
```

### requirements-dev.txt (开发依赖)
```
pytest>=7.4.0
pytest-cov>=4.1.0
hypothesis>=6.82.0
black>=23.7.0
mypy>=1.4.0
```

### 可选 ASR 依赖
```
funasr>=1.0.0          # 中文 ASR
openai-whisper>=20230314  # 多语言 ASR
```

