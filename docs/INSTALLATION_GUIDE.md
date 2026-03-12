# 安装和配置指南

## 入口变更说明（重要）

- 唯一支持的下载入口：`python 下载字幕.py`
- `python -m bilibili_extractor` / `bilibili-extractor` 已废弃为兼容壳入口（仅提示并退出）

## 1. 安装项目

```bash
git clone <repository-url>
cd bilibili-extractor
pip install -e .
```

## 2. 准备外部工具

将工具放到项目目录（推荐）：

```text
tools/BBDown/BBDown.exe
tools/ffmpeg/bin/ffmpeg.exe
tools/ffmpeg/bin/ffprobe.exe
```

## 3. 首次登录获取 Cookie

```bash
tools/BBDown/BBDown.exe --login
```

登录成功后会生成 `tools/BBDown/BBDown.data`。

## 4. 运行下载脚本

```bash
python 下载字幕.py
```

脚本会自动尝试：
- API 字幕（官方/AI）
- 失败后可选 ASR 兜底

## 5. 可选：安装 ASR 依赖

```bash
pip install funasr
# 或
pip install openai-whisper
```

## 6. 分发建议

打包时建议包含：
- `src/`
- `下载字幕.py`
- `config/`
- `tools/`（可选，体积较大）

并排除：
- `tools/BBDown/BBDown.data`（隐私敏感）
- `.git/`、`__pycache__/`

## 验证清单

- [ ] `tools/BBDown/BBDown.exe` 存在
- [ ] `tools/ffmpeg/bin/ffmpeg.exe` 存在
- [ ] `tools/BBDown/BBDown.data` 已生成（登录后）
- [ ] `python 下载字幕.py` 可启动交互界面

## 7. 第二流程模型配置

如果你要使用 `episode_draft` 的本地/远程大模型能力，推荐在项目根目录创建 `.env`：

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

- 只有模型和模型缓存放在 `D:\Model`
- 项目产物仍然保留在仓库目录内
- `episode_draft` 会自动读取项目根目录 `.env`

本地模型准备：

```powershell
$env:OLLAMA_MODELS="D:\Model\ollama"
ollama pull qwen2.5:3b
ollama serve
```

运行第二流程：

```bash
python -m episode_draft draft-from-bundle output/<bundle_dir> --backend auto
```
