# 项目目录结构说明

## 顶层结构

```text
D:\Kiro_proj\Test1/
├── src/                      # 核心源码
├── tests/                    # 单元与集成测试
├── config/                   # 配置文件
├── tools/                    # 外部工具（BBDown/FFmpeg）
├── docs/                     # 说明文档
├── samples/                  # 逐期回看样例数据
├── templates/                # 模板文件
├── output/                   # 运行产物（忽略提交）
├── temp/                     # 临时文件（忽略提交）
├── 下载字幕.py               # 视频采集主入口
├── review.py                 # 逐期回看 CLI 入口
└── pyproject.toml
```

## 源码结构

```text
src/
├── bilibili_extractor/
│   ├── __init__.py
│   ├── __main__.py           # 兼容壳入口（仅提示，不下载）
│   ├── core/                 # 配置、模型、主提取流程、异常
│   ├── modules/              # API、字幕、下载、ASR、归档等模块
│   └── utils/                # 工具函数
├── episode_draft/
│   ├── cli.py                # 第二流程命令行
│   ├── models.py             # EpisodeDraft 数据模型
│   ├── sentence_processor.py # 句级清洗与归一化
│   ├── block_builder.py      # 新闻块聚合
│   ├── draft_generator.py    # 草稿生成主流程
│   └── model_backend.py      # 本地/API/启发式分析后端
└── shuiqian_review/
    ├── cli.py                # 逐期回看命令行
    ├── models.py             # 节目包与新闻卡模型
    ├── rules.py              # 白名单来源与校验规则
    └── exporters.py          # 生产资料导出
```

## 当前两个入口

- `python 下载字幕.py`
  - 第一流程入口
  - 负责：下载原视频、获取 API/AI 字幕、必要时 ASR、生成标准化采集包
- `python -m episode_draft draft-from-bundle <bundle_dir>`
  - 第二流程入口
  - 负责：从标准化采集包生成 `EpisodeDraft.json`
- `python review.py`
  - 逐期回看骨架入口
  - 负责：初始化样板、校验节目包、导出生产资料

## 第一流程产物结构

```text
output/YYYY-MM-DD_标题_BVID/
├── raw/
│   ├── source_video.*
│   ├── video_metadata.json
│   └── subtitle_payload.json
├── derived/
│   ├── TranscriptBundle.json
│   ├── selected_track.txt
│   ├── selected_track.srt
│   └── source_audio.wav      # 仅 ASR 时存在
└── manifest/
    └── AssetManifest.json
```

## 工具目录要求

```text
tools/BBDown/BBDown.exe
tools/BBDown/BBDown.data      # 登录后生成
tools/ffmpeg/bin/ffmpeg.exe
tools/ffmpeg/bin/ffprobe.exe
```

## 测试结构

```text
tests/
├── integration/
├── property/
├── unit/
├── test_review_export.py
└── test_validation.py
```

运行建议：

```bash
set PYTHONPATH=src
pytest -q
```
