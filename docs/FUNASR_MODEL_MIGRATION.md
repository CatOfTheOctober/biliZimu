# FunASR 模型迁移与文件说明

## 迁移目标
- 将 ModelScope 已下载的 FunASR 相关模型从 `C:\Users\z\.cache\modelscope\hub\models\iic` 迁移到 `D:\Model\Funasr_model`。
- 仅移动，不保留 C 盘副本，不创建软链接。
- 后续新模型默认写入 `D:\Model\Funasr_model\modelscope_cache`。

## 本次已迁移目录
1. `speech_seaco_paraformer_large_asr_nat-zh-cn-16k-common-vocab8404-pytorch`（ASR 主识别）
2. `speech_fsmn_vad_zh-cn-16k-common-pytorch`（VAD 语音活动检测）
3. `punc_ct-transformer_cn-en-common-vocab471067-large`（标点恢复）

## 迁移后目录结构
```text
D:\Model\Funasr_model\
  ├─ speech_seaco_paraformer_large_asr_nat-zh-cn-16k-common-vocab8404-pytorch
  ├─ speech_fsmn_vad_zh-cn-16k-common-pytorch
  ├─ punc_ct-transformer_cn-en-common-vocab471067-large
  └─ modelscope_cache
```

## 关键文件功能说明

### 通用文件
- `model.pt`：模型权重文件（核心推理参数，体积最大）。
- `config.yaml` / `configuration.json`：模型结构、前后处理与推理配置。
- `README.md`：模型任务说明、示例与官方说明。
- `example/`：示例输入（音频/文本）。
- `fig/`：模型结构图、效果示意图。

### ASR 模型（speech_seaco_paraformer...）
- `tokens.json`：识别词表（token 到文本的映射基础）。
- `seg_dict`：分词/切分字典资源。
- `am.mvn`：声学特征归一化统计参数。

### VAD 模型（speech_fsmn_vad...）
- `am.mvn`：VAD 声学特征归一化统计参数。

### 标点模型（punc_ct-transformer...）
- `tokens.json`：标点模型词表。
- `jieba.c.dict` / `jieba_usr_dict`：中文分词词典资源，用于文本切分辅助。

### 隐藏元数据文件
- `.mdl` / `.msc` / `.mv`：ModelScope 本地缓存元信息（模型 ID、版本、文件清单、修订信息），用于缓存管理与版本追踪，不是推理权重本体。

## 环境变量配置（已设置）
- 用户级环境变量：
  - `MODELSCOPE_CACHE=D:\Model\Funasr_model\modelscope_cache`
- 说明：
  - 已写入 `HKCU\Environment`，对新开的终端生效。
  - 当前已运行终端可能需要重启后才会自动读取该值。

## 项目配置兼容性
- 当前项目默认配置已是 `funasr_model_path: D:/Model/Funasr_model`（见 `config/default_config.yaml` 和 `src/bilibili_extractor/core/config.py`）。
- `FunASREngine` 会扫描该目录下子目录并自动匹配 ASR/VAD/标点模型，无需改代码。

## 迁移校验结果（本次执行）
- D 盘目标目录存在，且 3 个模型目录均完整可见。
- C 盘原 3 个模型目录已移除。
- 关键文件存在性校验通过：
  - `model.pt`
  - `config.yaml`
  - `tokens.json`（适用模型）

## 建议的复核命令
```powershell
reg query HKCU\Environment /v MODELSCOPE_CACHE
Get-ChildItem D:\Model\Funasr_model
```

如需在“当前终端会话”立即生效，可临时执行：
```powershell
$env:MODELSCOPE_CACHE = "D:\Model\Funasr_model\modelscope_cache"
```
