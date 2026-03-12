# 第二流程模型接入说明

## 目标组合

- 本地模型：`Ollama + qwen2.5:3b`
- 远程模型：`DeepSeek / deepseek-chat`
- 模型与缓存目录统一放在 `D:\Model`
- 项目输出、草稿、review 文件继续放在项目目录中

## 目录约定

```text
D:\Model\
  ├─ Funasr_model\
  │   └─ modelscope_cache\
  └─ ollama\
```

项目内文件仍使用：

```text
D:\Kiro_proj\Test1\
  ├─ output\
  ├─ temp\
  ├─ docs\
  ├─ review\
  └─ .env
```

## 第一步：准备 `.env`

复制项目根目录的 `.env.example` 为 `.env`，填写实际值：

```text
MODELSCOPE_CACHE=D:\Model\Funasr_model\modelscope_cache
OLLAMA_MODELS=D:\Model\ollama

EPISODE_DRAFT_LOCAL_API_BASE=http://127.0.0.1:11434/v1
EPISODE_DRAFT_LOCAL_MODEL=qwen2.5:3b
EPISODE_DRAFT_LOCAL_API_KEY=

EPISODE_DRAFT_API_BASE=https://api.deepseek.com/v1
EPISODE_DRAFT_API_MODEL=deepseek-chat
EPISODE_DRAFT_API_KEY=<your_key>
```

说明：

- `EPISODE_DRAFT_LOCAL_API_KEY` 对 `Ollama` 默认可以留空
- `EPISODE_DRAFT_API_KEY` 需要填写你的 `DeepSeek` API Key
- `episode_draft` 会自动读取项目根目录 `.env`

## 第二步：准备本地模型

Windows PowerShell 示例：

```powershell
$env:OLLAMA_MODELS="D:\Model\ollama"
ollama pull qwen2.5:3b
ollama serve
```

如果你已经把 `OLLAMA_MODELS` 写进系统环境变量，重新开终端后可直接运行：

```powershell
ollama pull qwen2.5:3b
ollama serve
```

## 第三步：运行第二流程

推荐先用 `auto`：

```bash
python -m episode_draft doctor
python -m episode_draft draft-from-bundle output/<bundle_dir> --backend auto
```

后端模式说明：

- `auto`
  - 优先本地 `Qwen2.5:3b`
  - 低置信度、缺少原话锚点、主题归并不稳时再走 `DeepSeek`
- `local`
  - 只用本地模型
- `api`
  - 只用远程模型
- `heuristic`
  - 不使用大模型，只用启发式规则

## 推荐的分步验证方式

1. 先确认 `ollama serve` 正常运行
2. 先跑 `python -m episode_draft doctor`
3. 确认 `Local model` 和 `Remote model` 的 `ready` 状态符合预期
4. 用一个小样本跑 `--backend local`
5. 再跑 `--backend auto`
6. 对比输出中的：
   - `news_topics`
   - `segments`
   - `retrieval_keywords`
   - `quote_anchors`

## 常见问题

### 本地模型没有被调用

检查：

- `EPISODE_DRAFT_LOCAL_API_BASE` 是否可访问
- `ollama serve` 是否在运行
- `qwen2.5:3b` 是否已拉取

### 远程模型没有被调用

这是正常的，只要本地结果足够稳定，`auto` 不会强制调 `DeepSeek`。

### 输出里仍有 `needs_review`

这是预期行为。第二流程目标是减少人工整理量，不是完全免审。

## Prompt 分层

第二流程现在固定使用三层 prompt：

1. `sentence_analysis`
   - 目标：逐句判断是事实、评论、转场还是噪声
   - 输出：`sentence_type / topic_hint / confidence / is_host_commentary`

2. `segment_extract`
   - 目标：对连续时间段抽取结构化内容
   - 输出：`topic_candidate / tracking_scope_candidate / segment_summary / retrieval_keywords / host_view_summary / quote_anchors / angle_type / subscope_label`
   - 关键约束：
     - 不补外部知识
     - 关键词用于检索
     - 原话锚点必须来自输入句子
     - `angle_type` 只能从固定枚举中选

3. `topic_merge`
   - 目标：把多个时间段归并为可跟踪主题
   - 输出：`canonical_topic / tracking_scope / retrieval_keywords / host_overall_view_summary / segment_ids`
   - 关键约束：
     - 归并要看“后续跟踪边界是否相同”
     - 地方个案、责任主体、全国扩展不能随意混并

如果后面效果不理想，优先按职责定位问题：

- 句子类型错了：先改 `sentence_analysis`
- 时间段摘要、关键词、原话不稳：先改 `segment_extract`
- 同题合并不对：先改 `topic_merge`
