# 项目清理计划

## 目标

保持项目结构清晰，移除不相关的文档和临时文件，专注于核心功能。

## 清理范围

### 1. 临时测试文件（test_temp/）

这些文件是开发过程中的临时验证文件，已经被正式的单元测试替代：

- ✓ `test_temp/test_wbi_sign.py` - 已被 `tests/unit/test_bilibili_api_412_detection.py` 替代
- ✓ `test_temp/test_wbi_special_chars.py` - 已被 `tests/unit/test_bilibili_api_412_detection.py` 替代
- ✓ `test_temp/verify_fixes.py` - 临时验证脚本，不再需要

**建议**：删除这些文件

### 2. 过时的文档（docs/）

以下文档是开发过程中的中间产物，不再需要维护：

#### 可以删除的文档：
- `docs/BV1SpqhBbE7F_INVESTIGATION.md` - 特定视频的调查报告
- `docs/CACHE_AND_STABILITY_ISSUES.md` - 已解决的缓存问题
- `docs/CACHE_POLLUTION_ROOT_CAUSE.md` - 已解决的缓存污染问题
- `docs/CID_MULTIPAGE_DETAILED_EXPLANATION.md` - 多P视频处理的详细说明（已在代码中实现）
- `docs/DEFAULT_FORMAT_CHANGE.md` - 默认格式变更记录
- `docs/FINAL_STATUS_REPORT.md` - 最终状态报告
- `docs/MULTIPAGE_VIDEO_FIX.md` - 多P视频修复记录
- `docs/OUTPUT_PATH_FIX.md` - 输出路径修复记录
- `docs/RELATIVE_PATH_SUMMARY.md` - 相对路径总结
- `docs/REORGANIZATION_SUMMARY.md` - 重组总结
- `docs/STABILITY_FIX_SUMMARY.md` - 稳定性修复总结
- `docs/SUBBATCH_LOGIC_ANALYSIS.md` - SubBatch 逻辑分析
- `docs/test_cookie_usage.md` - Cookie 使用测试
- `docs/USER_GUIDE_CACHE_ISSUE.md` - 用户指南（缓存问题）

#### 需要保留的文档：
- ✓ `docs/AI_SUBTITLE_ANALYSIS.md` - AI 字幕技术分析（重要）
- ✓ `docs/COOKIE_GUIDE.md` - Cookie 使用指南（用户需要）
- ✓ `docs/INSTALLATION_GUIDE.md` - 安装指南（用户需要）
- ✓ `docs/PROJECT_STRUCTURE.md` - 项目结构说明（开发者需要）
- ✓ `docs/SUBBATCH_REFERENCE.md` - SubBatch 参考（开发者需要）
- ✓ `docs/SUBTITLE_FETCHING_ARCHITECTURE.md` - 字幕获取架构（新增，重要）

### 3. 代码中的不相关部分

#### WbiSigner 类（已弃用）

在 `src/bilibili_extractor/modules/bilibili_api.py` 中，存在一个 `WbiSigner` 类，但实际使用的是 `wbi_sign.py` 中的函数。

**建议**：
- 移除 `WbiSigner` 类
- 保留 `wbi_sign.py` 中的函数实现

#### 过时的方法

- `_ensure_wbi_keys()` - 已弃用，使用 `get_wbi_keys()` 替代
- `_get_wbi_keys()` - 已弃用，使用 `get_wbi_keys()` 替代

**建议**：移除这些方法

## 清理步骤

### 第一步：删除临时测试文件

```bash
rm test_temp/test_wbi_sign.py
rm test_temp/test_wbi_special_chars.py
rm test_temp/verify_fixes.py
```

### 第二步：删除过时的文档

```bash
rm docs/BV1SpqhBbE7F_INVESTIGATION.md
rm docs/CACHE_AND_STABILITY_ISSUES.md
rm docs/CACHE_POLLUTION_ROOT_CAUSE.md
rm docs/CID_MULTIPAGE_DETAILED_EXPLANATION.md
rm docs/DEFAULT_FORMAT_CHANGE.md
rm docs/FINAL_STATUS_REPORT.md
rm docs/MULTIPAGE_VIDEO_FIX.md
rm docs/OUTPUT_PATH_FIX.md
rm docs/RELATIVE_PATH_SUMMARY.md
rm docs/REORGANIZATION_SUMMARY.md
rm docs/STABILITY_FIX_SUMMARY.md
rm docs/SUBBATCH_LOGIC_ANALYSIS.md
rm docs/test_cookie_usage.md
rm docs/USER_GUIDE_CACHE_ISSUE.md
```

### 第三步：清理代码中的不相关部分

在 `src/bilibili_extractor/modules/bilibili_api.py` 中：
- 移除 `WbiSigner` 类
- 移除 `_ensure_wbi_keys()` 方法
- 移除 `_get_wbi_keys()` 方法

### 第四步：验证

运行测试确保没有破坏功能：

```bash
pytest tests/unit/ -v
pytest tests/integration/ -v
```

## 清理后的项目结构

```
docs/
├── AI_SUBTITLE_ANALYSIS.md              # AI 字幕技术分析
├── COOKIE_GUIDE.md                      # Cookie 使用指南
├── INSTALLATION_GUIDE.md                # 安装指南
├── PROJECT_STRUCTURE.md                 # 项目结构说明
├── SUBBATCH_REFERENCE.md                # SubBatch 参考
├── SUBTITLE_FETCHING_ARCHITECTURE.md    # 字幕获取架构（新增）
└── CLEANUP_PLAN.md                      # 清理计划（本文件）
```

## 核心文件保留

### 源代码
- ✓ `src/bilibili_extractor/modules/wbi_sign.py` - WBI 签名实现
- ✓ `src/bilibili_extractor/modules/bilibili_api.py` - B站 API 客户端
- ✓ `src/bilibili_extractor/modules/subtitle_fetcher.py` - 字幕获取器
- ✓ `src/bilibili_extractor/core/exceptions.py` - 异常定义
- ✓ `src/bilibili_extractor/core/config.py` - 配置管理

### 测试
- ✓ `tests/unit/test_rate_limiter_interval.py` - 速率限制测试
- ✓ `tests/unit/test_bilibili_api_412_detection.py` - 412 风控检测测试
- ✓ `tests/unit/test_risk_control_error.py` - 风控异常测试
- ✓ `tests/unit/test_subtitle_mismatch_error.py` - 字幕不匹配异常测试
- ✓ `tests/unit/test_config_api_settings.py` - 配置测试

## 清理效果

### 删除前
- 文档文件：21 个
- 临时测试文件：3 个
- 总计：24 个不必要的文件

### 删除后
- 文档文件：6 个（精简 71%）
- 临时测试文件：0 个
- 总计：6 个必要的文件

## 维护建议

1. **定期审查** - 每个月审查一次文档，删除过时的内容
2. **命名规范** - 临时文件使用 `_temp` 或 `_draft` 后缀
3. **版本控制** - 使用 Git 标签标记重要版本
4. **文档更新** - 代码变更时同步更新相关文档

## 注意事项

- 删除前确保所有功能都有测试覆盖
- 删除前备份重要信息
- 删除后运行完整的测试套件
- 更新 README.md 中的文档链接
