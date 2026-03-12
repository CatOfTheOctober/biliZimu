# 当前项目状态

## 当前定位

这个仓库现在有两条已经成型的工作线：

1. `B站视频采集与标准化`
2. `《睡前消息》逐期回看骨架`

其中第一条已经能跑真实视频，第二条已经有数据结构、校验和导出骨架，并新增了独立的内容草稿生成包。

## 已完成的核心任务

### 1. 统一下载入口

- 主入口固定为 `python 下载字幕.py`
- `python -m bilibili_extractor` 只保留兼容壳，不再承担下载流程

### 2. 第一流程标准化产物

已经完成“下载 -> 提取 -> 标准化 -> 归档”的第一流程，并固定产物结构：

- `raw/`
  - 原始视频
  - 页面元数据
  - 原始字幕/API 原件
- `derived/`
  - `TranscriptBundle.json`
  - `selected_track.txt`
  - `selected_track.srt`
  - ASR 时生成的派生音频
- `manifest/`
  - `AssetManifest.json`

### 3. 视频优先归档策略

- 即使 API/AI 字幕可用，也先下载原视频
- 成功标准不再是“拿到字幕”，而是“原始视频 + 元数据 + 标准化字幕包”都存在
- 失败时也保留失败包，便于补跑和排查

### 4. API 字幕主链路

- 优先走 B 站 API 字幕
- 支持 AI 字幕优先，普通平台字幕回退
- Cookie/WBI 相关逻辑已经收敛到库内模块，不再放在脚本层硬拼

### 5. ASR 回退链路

- API 字幕失败后可回退到 ASR
- 已验证 `conda activate py311` 环境下可以正常调用本地 FunASR
- 本地模型目录 `D:\Funasr_model` 已能被默认缓存路径复用

### 6. ASR 细粒度时间戳

- 已修复 FunASR 在真实视频上的“整段文本无有效时间轴”问题
- 现在可把字级时间戳重组为一句话一级的时间段
- 已在真实视频 `BV1p9AozWEF2` 上验证，输出可直接用于后续视频时间轴对齐

### 7. 《睡前消息》逐期回看骨架

已新增本地优先的逐期回看模块：

- `review.py`
- `src/shuiqian_review/`
- `templates/episode_template.json`
- `samples/episode_2019-11-07.sample.json`

当前已具备：

- 节目包模板初始化
- 白名单信源校验
- 样例节目导出 `production pack`

### 8. 第二流程内容草稿生成

已新增独立源码包：

- `src/episode_draft/`

当前已具备：

- 从 `TranscriptBundle.json` 读取句级时间轴
- 自动清理残句与明显噪声
- 自动归并新闻块
- 自动抽取主持人评论候选
- 自动生成 `EpisodeDraft.json`

## 当前目录重点

```text
src/
  bilibili_extractor/      # 采集与标准化主工程
  episode_draft/           # 第二流程：内容草稿生成
  shuiqian_review/         # 逐期回看骨架
docs/                      # 说明文档
samples/                   # 逐期回看样例输入
templates/                 # 模板文件
tests/                     # 单元/集成测试
output/                    # 运行产物（忽略提交）
temp/                      # 临时文件（忽略提交）
下载字幕.py                 # 唯一推荐下载入口
review.py                  # 逐期回看 CLI 入口
```

## 已验证内容

- 第一流程自动化测试通过
- AI 字幕相关集成测试通过
- FunASR 时间戳解析测试通过
- 真实视频 `BV1p9AozWEF2` 已成功生成标准化采集包

## 当前仍未完成的部分

### 采集层

- API 字幕失败原因还没有进一步分类沉淀为更细的诊断字段
- 失败包目前按视频目录复用，同视频多次运行不会保留独立 run 历史

### 内容层

- 已能从 `TranscriptBundle.json` 自动切出新闻块草稿
- 已能自动抽主持人原话候选、标题候选和问题定义候选
- 还没有人工确认后的正式 `EpisodePackage` 转换入口

### 跟踪层

- 还没有新闻后续时间线抓取和证据归档流程
- 还没有官方/主流媒体来源库自动辅助检索

### 输出层

- 还没有从采集包直接生成 `NewsCard`
- 还没有从多条新闻卡自动拼成单期脚本提纲

## 建议的下一步

最合理的下一步不是继续扩第一流程，而是开始第二流程：

`TranscriptBundle -> 新闻切分 -> 原话提取 -> NewsCard`

建议优先定三件事：

1. 单期节目中“新闻边界”的判定规则
2. 主持人原话摘录的字段模板
3. `NewsCard` 的正式 JSON 结构
