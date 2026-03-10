# 快速开始指南

## 项目安装

### 前置要求
- Python 3.8+
- pip 包管理器

### 安装步骤

#### 方式 1: 开发模式安装（推荐）
```bash
# 进入项目目录
cd D:\Kiro_proj\Test1

# 安装项目（开发模式）
pip install -e .

# 安装开发依赖
pip install -r requirements-dev.txt
```

#### 方式 2: 直接使用 python -m
```bash
# 如果安装失败，可以使用以下方式
python -m bilibili_extractor --help
```

### 验证安装
```bash
# 检查是否安装成功
bilibili-extractor --help

# 或使用 python -m
python -m bilibili_extractor --help
```

## 获取 Cookie

### 方式 1: 使用 BBDown 登录（推荐）
```bash
# 运行 BBDown 进行登录
tools/BBDown/BBDown.exe --login

# BBDown 会自动保存 Cookie 到 tools/BBDown/cookie.txt
```

### 方式 2: 手动获取 Cookie
1. 打开浏览器，访问 https://www.bilibili.com
2. 登录你的账号
3. 打开开发者工具（F12）
4. 进入 Application → Cookies
5. 复制所有 Cookie（或至少包含 SESSDATA 和 DedeUserID）
6. 将 Cookie 保存到 `tools/BBDown/cookie.txt`

### Cookie 格式
Cookie 应该是这样的格式：
```
SESSDATA=xxx; DedeUserID=xxx; bili_jct=xxx; ...
```

## 使用项目

### 基本用法
```bash
# 提取视频字幕
bilibili-extractor "https://www.bilibili.com/video/BV1M8c7zSEBQ/"

# 或使用 python -m
python -m bilibili_extractor "https://www.bilibili.com/video/BV1M8c7zSEBQ/"
```

### 检查 Cookie 状态
```bash
bilibili-extractor --check-cookie
```

### 使用配置文件
```bash
bilibili-extractor "VIDEO_URL" --config config/config.yaml
```

## 当前已知问题

### 问题 1: AI 字幕 API 返回 404
**症状**：无法获取 AI 字幕
**原因**：AI 字幕 API 可能已改变或需要特殊参数
**解决方案**：
1. 确保已提供有效的 Cookie
2. 等待我们修复 API 端点
3. 或使用浏览器自动化方案

### 问题 2: Cookie 文件不存在
**症状**：提示 Cookie 文件不存在
**原因**：未运行 BBDown 登录
**解决方案**：
1. 运行 `tools/BBDown/BBDown.exe --login`
2. 或手动将 Cookie 放在 `tools/BBDown/cookie.txt`

### 问题 3: 字幕获取不稳定
**症状**：有时能获取，有时不能
**原因**：Cookie 过期或 API 限流
**解决方案**：
1. 重新登录获取新的 Cookie
2. 等待一段时间后重试
3. 检查网络连接

## 诊断和调试

### 运行诊断脚本
```bash
# 诊断 WBI API
python test_wbi_api_debug.py

# 诊断 Cookie 和 AI 字幕 API
python test_cookie_and_ai_subtitle.py
```

### 查看详细日志
```bash
# 设置日志级别为 DEBUG
python -m bilibili_extractor "VIDEO_URL" --log-level DEBUG
```

## 项目结构

```
D:\Kiro_proj\Test1/
├── src/bilibili_extractor/          # 源代码
│   ├── core/                        # 核心模块
│   ├── modules/                     # 功能模块
│   └── utils/                       # 工具函数
├── tests/                           # 测试
├── config/                          # 配置文件
├── tools/                           # 外部工具
│   ├── BBDown/                      # BBDown 下载器
│   │   ├── BBDown.exe
│   │   └── cookie.txt               # Cookie 文件
│   └── ffmpeg/                      # FFmpeg
├── docs/                            # 文档
├── output/                          # 输出目录
└── temp/                            # 临时文件
```

## 常见问题

### Q: 如何更新项目？
A: 使用 `pip install -e .` 重新安装，或直接修改源代码。

### Q: 如何运行测试？
A: 使用 `pytest tests/` 运行所有测试。

### Q: 如何生成覆盖率报告？
A: 使用 `pytest tests/ --cov=src/bilibili_extractor --cov-report=html`。

### Q: 支持哪些输出格式？
A: 支持 SRT、JSON、TXT、Markdown 等格式。

### Q: 支持批量处理吗？
A: 支持，可以在配置文件中指定多个视频 URL。

## 获取帮助

### 查看帮助信息
```bash
bilibili-extractor --help
```

### 查看详细文档
- `README.md` - 项目说明
- `docs/PROJECT_STRUCTURE.md` - 项目结构
- `docs/COOKIE_GUIDE.md` - Cookie 使用指南
- `DIAGNOSIS_REPORT.md` - 诊断报告

### 报告问题
如果遇到问题，请：
1. 运行诊断脚本
2. 查看日志输出
3. 检查 Cookie 是否有效
4. 提供详细的错误信息

## 下一步

1. **安装项目**：`pip install -e .`
2. **获取 Cookie**：运行 BBDown 登录
3. **测试项目**：`bilibili-extractor "VIDEO_URL"`
4. **查看输出**：检查 `output/` 目录

祝你使用愉快！
