# B站字幕提取工具 - 快速使用指南

这个项目提供了一个非常简便的方式来下载和提取 Bilibili 视频的字幕。以下是快速上手的步骤：

## 🚀 三步快速开始

### 1. 初始安装
如果你是第一次使用，需要安装基础的依赖包。
在项目目录下，双击运行 `安装.bat` 文件，或者打开命令行终端执行以下命令：
```bash
pip install requests pyyaml
```
*(注意：如果你需要识别无字幕的视频，还需要安装 `funasr` 或 `openai-whisper` 等语音识别库)*

### 2. 获取 Cookie（强烈建议）
为了能够获取 B站的 **AI生成字幕** 以及高清/大会员视频的字幕，你需要进行登录获取 Cookie：
1. 打开终端（CMD 或 PowerShell）。
2. 进入 BBDown 文件夹：`cd tools/BBDown`
3. 运行登录命令：`BBDown.exe --login`
4. 此时会弹出二维码或提示，请使用 Bilibili 手机端扫码登录。登录成功后，会在该目录下生成一个 `BBDown.data` 文件，系统之后会自动读取它。

### 3. 开始下载字幕
回到项目根目录，运行简化版的下载脚本：
```bash
python 下载字幕.py
```
运行后，程序会提示你输入你想下载的视频链接或 ID。支持以下三种输入格式：
- **完整 URL**：`https://www.bilibili.com/video/BV1M8c7zSEBQ/`
- **短链接**：`https://b23.tv/xxxxx`
- **直接 BVID**：`BV1M8c7zSEBQ`

输入后回车，程序会自动解析、下载并保存字幕。

---

## 📁 查看输出文件

所有的下载结果都会保存在项目根目录下的 `output/` 文件夹中。
默认会生成两个文件：
- `视频标题_BVID.txt`：纯文本格式，去除了时间轴，适合直接阅读。
- `视频标题_BVID.srt`：标准字幕格式，包含时间轴，适合导入剪辑软件或播放器使用。

## 💡 进阶使用（命令行模式）
如果你需要更多的高级功能，可以直接调用核心模块 `bilibili_extractor`：
```bash
# 提取并指定输出格式为 json
python -m bilibili_extractor "你的视频链接" --format json

# 对无字幕视频强制使用 whisper 语音识别（需提前安装 openai-whisper）
python -m bilibili_extractor "你的视频链接" --asr-engine whisper
```
