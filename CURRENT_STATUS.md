# 项目当前状态

## ✅ 可用功能

### 推荐使用方式：`下载字幕.py` 脚本

这是目前最稳定的使用方式，已验证可以成功下载 AI 字幕。

**使用步骤：**

1. **安装依赖**
   ```bash
   pip install -e .
   ```

2. **获取 Cookie**
   ```bash
   cd tools/BBDown
   BBDown.exe --login
   ```

3. **下载字幕**
   ```bash
   python 下载字幕.py
   ```

**支持的输入格式：**
- 完整 URL: `https://www.bilibili.com/video/BV1M8c7zSEBQ/`
- 短链接: `https://b23.tv/xxxxx`
- 直接 BVID: `BV1M8c7zSEBQ`

**输出文件：**
- `output/视频标题_BVID.txt` - 纯文本格式
- `output/视频标题_BVID.srt` - SRT 字幕格式

## ⚠️ 已知问题

### 命令行工具 WBI 签名 412 错误

使用 `bilibili-extractor` 命令时会遇到 412 错误：

```
WBI请求处理出错: 412 Client Error: Precondition Failed
```

**原因：** B站的 WBI 签名验证机制更新，导致现有实现无法通过验证。

**解决方案：** 使用 `下载字幕.py` 脚本，该脚本使用简化的 API 调用方式，可以绕过 WBI 签名问题。

## 📊 测试结果

已成功测试多个视频，包括：
- AI 字幕视频 ✅
- 官方字幕视频 ✅
- 多语言字幕 ✅

## 🔧 技术细节

### 工作原理

`下载字幕.py` 脚本：
1. 直接调用 `BilibiliAPI.get_subtitle_with_ai_fallback()` 方法
2. 使用 Cookie 进行身份验证
3. 自动处理 AI 字幕和官方字幕的降级逻辑
4. 保存为 TXT 和 SRT 两种格式

### 核心 API

```python
from bilibili_extractor.modules.bilibili_api import BilibiliAPI

api = BilibiliAPI(cookie=cookie)
result = api.get_subtitle_with_ai_fallback(bvid, cid)
```

## 📝 文档

- **快速开始**: `README_简单使用.md`
- **详细指南**: `使用指南.md`
- **项目结构**: `docs/PROJECT_STRUCTURE.md`
- **Cookie 指南**: `docs/COOKIE_GUIDE.md`

## 🎯 下一步计划

1. 修复 WBI 签名问题（如果需要）
2. 优化批量下载功能
3. 添加更多输出格式支持
4. 改进错误处理和日志

---

**最后更新**: 2026-03-10  
**状态**: ✅ 核心功能可用，推荐使用 `下载字幕.py` 脚本
