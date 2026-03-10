# 发现

## 需求
1. 临时目录应该位于项目根目录的 `temp/` 文件夹
2. `bilibili_extractor` 目录应该只包含源码
3. 路径解析应该正确处理相对路径

## 研究发现

### 当前问题分析
1. **Config 类定义**：
   - `temp_dir` 默认值为 `"./temp"`
   - `resolve_path` 方法会将相对路径解析为相对于项目根目录的路径

2. **代码使用情况**：
   - `video_downloader.py` 和 `subtitle_fetcher.py` 使用 `Path(self.config.temp_dir)` 创建目录
   - `cli.py` 中只对 `output_dir` 调用了 `resolve_path`，没有对 `temp_dir` 调用

3. **路径解析问题**：
   - 当代码使用 `Path(self.config.temp_dir)` 时，如果当前工作目录是 `src/bilibili_extractor`，那么 `"./temp"` 会被解析为 `src/bilibili_extractor/temp`
   - 这就是为什么临时目录出现在错误位置的原因

## 技术决策
| 决策 | 考虑的选项 | 选择 | 原因 |
|------|------------|------|------|
| 如何修复路径解析 | 1. 修改所有使用 temp_dir 的地方调用 resolve_path<br>2. 修改 Config 类自动解析路径 | 选项 2 | 更简洁，确保所有地方都使用解析后的路径 |
| 测试目录位置 | 1. 保持现有测试目录<br>2. 更新测试使用正确的路径 | 选项 2 | 确保测试反映实际使用情况 |

## 资源
- `src/bilibili_extractor/core/config.py` - Config 类定义
- `src/bilibili_extractor/modules/video_downloader.py` - 视频下载器
- `src/bilibili_extractor/modules/subtitle_fetcher.py` - 字幕获取器
- `src/bilibili_extractor/cli.py` - CLI 入口
## 最终实现

### 修改的文件
1. **`src/bilibili_extractor/core/config.py`**:
   - 添加了 `__post_init__` 方法来自动解析路径
   - 添加了 `resolved_temp_dir` 和 `resolved_output_dir` 属性
   - 保持了向后兼容性，`temp_dir` 字段仍然存储原始值

2. **`src/bilibili_extractor/modules/video_downloader.py`**:
   - 将 `Path(self.config.temp_dir)` 改为 `self.config.resolved_temp_dir`

3. **`src/bilibili_extractor/modules/subtitle_fetcher.py`**:
   - 将 `Path(self.config.temp_dir)` 改为 `self.config.resolved_temp_dir`

4. **`src/bilibili_extractor/core/extractor.py`**:
   - 将 `config.temp_dir` 改为 `str(config.resolved_temp_dir)`

5. **`tests/unit/test_temp_dir_resolution.py`**:
   - 创建了新的测试文件来验证路径解析功能

### 解决的问题
1. **路径解析问题**: 之前代码使用 `Path(self.config.temp_dir)` 时，如果当前工作目录是 `src/bilibili_extractor`，那么 `"./temp"` 会被解析为 `src/bilibili_extractor/temp`
2. **目录混乱问题**: 临时文件现在正确存储在项目根目录的 `temp/` 目录，而不是 `src/bilibili_extractor/temp`
3. **源码纯净性**: `bilibili_extractor` 目录现在只包含源码，不包含临时文件

### 验证结果
- 所有新创建的测试用例通过
- 基本功能测试通过
- 路径解析正确：`"./temp"` → `E:\Kiro_proj\Test1\temp`
- 临时目录现在位于项目根目录，而不是源码目录