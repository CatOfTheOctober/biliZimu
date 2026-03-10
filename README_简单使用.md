# B站字幕提取工具 - 简单使用版

## 🚀 三步开始使用

### 第一步：安装
双击运行 `安装.bat` 或手动执行：
```bash
pip install requests pyyaml
```

### 第二步：获取 Cookie（重要！）
```bash
# 进入 BBDown 目录
cd tools/BBDown

# 登录获取 Cookie
BBDown.exe --login
```
按提示扫码或输入账号密码完成登录。

### 第三步：下载字幕
```bash
# 运行下载工具
python 下载字幕.py
```
然后输入视频 URL 或 BVID 即可。

## 📋 支持的输入格式

- 完整 URL：`https://www.bilibili.com/video/BV1M8c7zSEBQ/`
- 短链接：`https://b23.tv/xxxxx`
- 直接 BVID：`BV1M8c7zSEBQ`

## 📁 输出文件

字幕会保存在 `output/` 目录：
- `视频标题_BVID.txt` - 纯文本格式（默认）
- `视频标题_BVID.srt` - 标准字幕格式

## ❓ 常见问题

**Q: 提示"未找到字幕"？**
A: 确保视频有字幕，并且已获取 Cookie

**Q: Cookie 如何获取？**
A: 运行 `tools/BBDown/BBDown.exe --login` 并完成登录

**Q: 支持哪些字幕？**
A: 支持 AI 字幕和官方字幕，多种语言

## 🎯 快速测试

可以用这个视频测试：
```
https://www.bilibili.com/video/BV1M8c7zSEBQ/
```

---

**更详细的使用说明请查看 `使用指南.md`**