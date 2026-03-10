# 缓存问题用户指南

## 问题描述

你可能遇到以下情况：
- 提取的字幕内容与视频标题不匹配
- 不同视频提取到相同的字幕
- 清空output目录后重新提取就正常了

这是由于**缓存污染**导致的。

## 已实施的修复

我们已经实施了以下修复：

1. ✅ 修复了缓存键污染问题（page超出范围）
2. ✅ 降低了请求频率（从2个/秒到1个/秒）
3. ✅ 缩短了缓存TTL（从3600秒到60秒）
4. ✅ 确保每次运行程序都创建新的API实例

## 如何避免缓存问题

### 方法1：每次提取前清空output目录（推荐）

```bash
# Windows PowerShell
Remove-Item output/*.txt -Force
python -m bilibili_extractor "VIDEO_URL"

# Linux/Mac
rm -rf output/*
python -m bilibili_extractor "VIDEO_URL"
```

### 方法2：等待60秒后再提取下一个视频

缓存TTL现在是60秒，等待60秒后缓存会自动过期。

```bash
python -m bilibili_extractor "VIDEO_URL_1"
sleep 60
python -m bilibili_extractor "VIDEO_URL_2"
```

### 方法3：每次提取后检查内容

提取完成后，打开output目录中的文件，检查前几行内容是否与视频标题匹配。

```bash
python -m bilibili_extractor "VIDEO_URL"
# 检查 output/BVID.txt 的前几行
head -20 output/BVID.txt
```

## 如何验证字幕是否正确

1. **检查视频标题**：
   ```bash
   python check_video.py BVID
   ```

2. **检查字幕内容**：
   打开output目录中的txt文件，查看前10-20行

3. **对比关键词**：
   - 如果视频是关于"固态电池"，字幕中应该包含"固态"、"电池"等关键词
   - 如果视频是关于"刀片电池"，字幕中应该包含"刀片"、"比亚迪"等关键词

## 常见问题

### Q1：为什么会出现缓存污染？

A：缓存机制是为了提高性能，避免重复请求API。但在某些情况下，缓存键可能冲突，导致不同视频的数据混淆。

### Q2：禁用缓存会怎样？

A：禁用缓存会导致每次请求都调用API，速度较慢，且可能触发B站的限流机制。

### Q3：缓存TTL是什么？

A：TTL（Time To Live）是缓存的生存时间。当前设置为60秒，意味着缓存数据在60秒后会自动过期。

### Q4：如何彻底清除缓存？

A：缓存是内存级别的，重启Python进程即可清除。或者等待60秒让缓存自动过期。

## 测试示例

### 测试1：连续提取两个不同视频

```bash
# 清空output目录
rm -rf output/*

# 提取视频1
python -m bilibili_extractor "https://www.bilibili.com/video/BV1M8c7zSEBQ"
# 检查output/BV1M8c7zSEBQ.txt，应该是固态电池内容

# 等待60秒
sleep 60

# 提取视频2
python -m bilibili_extractor "https://www.bilibili.com/video/BV1ZLPSzFE6c"
# 检查output/BV1ZLPSzFE6c.txt，应该是刀片电池内容
```

### 测试2：验证缓存过期

```bash
# 第一次提取
python -m bilibili_extractor "VIDEO_URL"
# 记录耗时（例如：3.5秒）

# 立即第二次提取（应该使用缓存）
python -m bilibili_extractor "VIDEO_URL"
# 记录耗时（应该更快，例如：0.5秒）

# 等待60秒后第三次提取（缓存已过期）
sleep 60
python -m bilibili_extractor "VIDEO_URL"
# 记录耗时（应该和第一次类似，例如：3.5秒）
```

## 报告问题

如果你仍然遇到缓存问题，请提供以下信息：

1. **视频URL**
2. **预期的视频标题**
3. **实际提取的字幕前10行**
4. **提取日志**（使用`--log-level DEBUG`）
5. **是否清空了output目录**
6. **两次提取之间的时间间隔**

示例：
```bash
python -m bilibili_extractor "VIDEO_URL" --log-level DEBUG > debug.log 2>&1
```

然后将debug.log和output文件一起提供。

## 总结

- ✅ 系统已经实施了多项修复来减少缓存污染
- ✅ 缓存TTL已缩短到60秒
- ✅ 每次运行程序都会创建新的API实例
- ⚠️ 建议每次提取前清空output目录
- ⚠️ 或者等待60秒后再提取下一个视频

如果遵循这些建议，应该能够避免大部分缓存问题。
