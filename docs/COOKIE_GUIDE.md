# B站Cookie使用指南

## 快速开始

### 1. 获取B站Cookie

#### 最简单的方法（推荐）：

1. 在Chrome/Edge浏览器中登录B站
2. 安装扩展：[Get cookies.txt LOCALLY](https://chrome.google.com/webstore/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc)
3. 访问 https://www.bilibili.com
4. 点击扩展图标，选择"Export"
5. 保存为 `bilibili_cookie.txt`

#### 手动方法：

1. 在浏览器中登录B站
2. 按F12打开开发者工具
3. 切换到"Application"标签（Chrome）或"Storage"标签（Firefox）
4. 左侧选择"Cookies" → "https://www.bilibili.com"
5. 找到以下重要Cookie：
   - `SESSDATA` - 最重要，必须有
   - `bili_jct`
   - `DedeUserID`

6. 创建文本文件 `bilibili_cookie.txt`，格式如下：

```
# Netscape HTTP Cookie File
.bilibili.com	TRUE	/	FALSE	1735689600	SESSDATA	你的SESSDATA值
.bilibili.com	TRUE	/	FALSE	1735689600	bili_jct	你的bili_jct值
.bilibili.com	TRUE	/	FALSE	1735689600	DedeUserID	你的DedeUserID值
```

### 2. 使用Cookie运行工具

```bash
# 基本用法
python -m bilibili_extractor "视频URL" --cookie bilibili_cookie.txt

# 你的视频示例
python -m bilibili_extractor "https://www.bilibili.com/video/BV1bicgzaEA3" --cookie bilibili_cookie.txt
```

## 为什么需要Cookie？

某些B站视频需要登录才能：
- 查看字幕
- 下载高清视频
- 访问大会员内容
- 访问付费内容

如果不提供Cookie，BBDown无法获取这些内容。

## 验证Cookie是否有效

### 方法1：使用BBDown测试
```bash
BBDown "https://www.bilibili.com/video/BV1bicgzaEA3" --sub-only --cookie bilibili_cookie.txt
```

如果成功下载字幕，说明Cookie有效。

### 方法2：查看工具日志
运行工具后，查看输出：
- ✅ 成功：`[INFO] Official subtitle found, downloading...`
- ❌ 失败：`[INFO] No subtitles found, proceeding with ASR workflow`

## 常见问题

### Q1: Cookie过期了怎么办？
A: Cookie通常有效期为几个月。过期后需要重新获取：
1. 在浏览器中重新登录B站
2. 按照上述步骤重新导出Cookie

### Q2: 提供了Cookie还是说没有字幕？
A: 可能的原因：
1. Cookie文件路径错误 - 检查文件是否存在
2. Cookie格式错误 - 确保使用正确的格式
3. Cookie已过期 - 重新获取Cookie
4. 视频确实没有字幕 - 在浏览器中确认视频是否有CC字幕按钮

### Q3: 不想用Cookie，能直接用ASR吗？
A: 可以，但需要安装ASR库：
```bash
# 安装FunASR（推荐用于中文）
pip install funasr

# 或安装Whisper（多语言）
pip install openai-whisper
```

然后运行：
```bash
python -m bilibili_extractor "视频URL"
```

系统会自动检测没有字幕，然后使用ASR。

## 针对你当前问题的解决方案

你的错误信息显示：
```
[INFO] No subtitles found, proceeding with ASR workflow
[ERROR] ASR library not installed: FunASR not installed
```

这说明：
1. 没有获取到字幕（可能因为没有Cookie）
2. FunASR未正确安装

### 解决步骤：

#### 步骤1：先尝试用Cookie获取字幕（推荐）
```bash
# 1. 获取Cookie文件（按照上面的方法）
# 2. 运行命令
python -m bilibili_extractor "https://www.bilibili.com/video/BV1bicgzaEA3" --cookie bilibili_cookie.txt
```

如果成功，你会看到：
```
[INFO] Official subtitle found, downloading...
[INFO] Downloaded 1 subtitle file(s)
[INFO] Parsing subtitle file
```

#### 步骤2：如果还是没有字幕，安装ASR
```bash
# 检查FunASR是否真的安装了
python -c "from funasr import AutoModel; print('FunASR installed')"

# 如果报错，重新安装
pip uninstall funasr -y
pip install funasr

# 或者使用Whisper
pip install openai-whisper
python -m bilibili_extractor "视频URL" --asr-engine whisper --cookie bilibili_cookie.txt
```

## Cookie安全提示

⚠️ **重要**：Cookie包含你的登录凭证，请妥善保管！

- 不要分享Cookie文件给他人
- 不要上传Cookie到公共仓库
- 定期更换密码会使Cookie失效
- 使用完毕后可以删除Cookie文件

## 配置文件方式（可选）

如果经常使用，可以创建配置文件 `config.yaml`：

```yaml
# config.yaml
cookie_file: "bilibili_cookie.txt"
output_dir: "./output"
log_level: "INFO"
asr_engine: "funasr"
```

然后运行：
```bash
python -m bilibili_extractor "视频URL" --config config.yaml
```
