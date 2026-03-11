# 项目目录结构说明

## 顶层结构

```text
D:\Kiro_proj\Test1/
├── src/                      # 核心源码
├── tests/                    # 测试
├── config/                   # 配置
├── tools/                    # 外部工具（BBDown/FFmpeg）
├── docs/                     # 文档
├── output/                   # 输出目录
├── temp/                     # 临时目录
├── 下载字幕.py               # 唯一下载入口
└── pyproject.toml
```

## 源码结构

```text
src/bilibili_extractor/
├── __init__.py
├── __main__.py               # 兼容壳入口（仅提示，不下载）
├── core/                     # 配置、模型、主提取流程、异常
├── modules/                  # API、字幕、下载、ASR 等功能模块
└── utils/                    # 工具函数
```

## 入口说明

- 推荐入口：`python 下载字幕.py`
- 兼容壳入口：`python -m bilibili_extractor`（仅输出迁移提示）

## 工具目录要求

```text
tools/BBDown/BBDown.exe
tools/BBDown/BBDown.data      # 登录后生成
tools/ffmpeg/bin/ffmpeg.exe
tools/ffmpeg/bin/ffprobe.exe
```

## 测试说明

- 测试目录：`tests/unit`、`tests/integration`、`tests/property`
- 运行建议：

```bash
set PYTHONPATH=src
pytest -q
```
