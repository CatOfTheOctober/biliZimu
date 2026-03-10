# AI 字幕获取问题诊断报告

## 执行摘要

经过详细诊断，我们发现了 Python 版本 AI 字幕获取失败的根本原因，并提出了两个解决方案。

## 诊断发现

### 1. WBI 签名问题 ✅ 已解决
**问题**：Python 版本对 `/x/player/wbi/v2` 进行了 WBI 签名
**原因**：误解了 B 站 API 的要求
**解决方案**：已移除 WBI 签名，直接使用原始 URL
**状态**：✅ 已修复

### 2. AI 字幕 API 返回 404 ⚠️ 需要调查
**问题**：调用 `/x/player/v2/ai/subtitle/search/stat` 返回 404
**可能原因**：
- API 端点已改变
- 需要特殊的请求参数
- 需要有效的 Cookie
- API 可能已被 B 站移除或改变

**当前状态**：需要进一步调查

### 3. Cookie 不可用 ⚠️ 用户需要提供
**问题**：BBDown Cookie 文件不存在
**原因**：用户未运行 BBDown 登录
**解决方案**：
- 用户需要运行 BBDown 进行登录
- 或手动将 Cookie 放在 `tools/BBDown/cookie.txt`
- Cookie 需要包含 `SESSDATA` 和 `DedeUserID`

## 当前代码状态

### 已完成的修复
✅ 移除了 WBI 签名
✅ 添加了完整的请求头（包括 X-Wbi-UA）
✅ 创建了统一的字幕获取函数
✅ 所有单元测试通过（24/24）

### 待解决的问题
⚠️ AI 字幕 API 返回 404
⚠️ Cookie 管理和验证
⚠️ 不稳定性问题

## 建议的解决方案

### 方案 A: 继续修复 API 方案（推荐）
**优点**：
- 更稳定、更可靠
- 不依赖浏览器
- 可以批量处理

**步骤**：
1. 调查 AI 字幕 API 的确切端点和参数
2. 验证 Cookie 的必要性
3. 添加 Cookie 验证和刷新机制
4. 测试多个视频

**预计工作量**：中等

### 方案 B: 浏览器自动化方案（备选）
**优点**：
- 完全模拟浏览器行为
- 不受 API 变化影响
- 可以获取任何浏览器能获取的内容

**缺点**：
- 依赖浏览器和驱动程序
- 性能较低
- 不适合批量处理

**实现方式**：
- 使用 Selenium 或 Puppeteer
- 直接在浏览器中运行 SubBatch 插件
- 或模拟浏览器的请求流程

**预计工作量**：较大

## 立即行动项

### 1. 验证 API 端点（优先级：高）
```bash
# 使用 curl 测试 API
curl -H "Cookie: YOUR_COOKIE" \
  "https://api.bilibili.com/x/player/v2/ai/subtitle/search/stat?aid=116061995271743&cid=36030054817"
```

### 2. 检查 JS 版本的实际请求（优先级：高）
- 打开浏览器开发者工具
- 运行 SubBatch 插件
- 查看网络请求
- 对比 Python 版本的请求

### 3. 获取有效的 Cookie（优先级：中）
- 运行 BBDown 进行登录
- 或从浏览器中复制 Cookie
- 放在 `tools/BBDown/cookie.txt`

### 4. 测试完整流程（优先级：中）
- 使用有效的 Cookie 进行测试
- 测试多个视频
- 验证字幕质量

## 技术细节

### API 端点对比

| 端点 | 用途 | 需要签名 | 需要 Cookie |
|------|------|---------|-----------|
| `/x/player/wbi/v2` | 获取播放器信息 | ❌ 否 | ❌ 否 |
| `/x/player/v2/ai/subtitle/search/stat` | 获取 AI 字幕 URL | ❌ 否 | ✅ 是 |
| `/x/space/wbi/arc/search` | 搜索用户视频 | ✅ 是 | ❌ 否 |

### 请求头配置

Python 版本已包含所有必需的请求头：
- `User-Agent`: Chrome 浏览器标识
- `Accept`: application/json
- `Accept-Language`: zh-CN
- `Origin`: https://www.bilibili.com
- `Referer`: https://www.bilibili.com/
- `X-Wbi-UA`: Win32.Chrome.109.0.0.0（关键）
- `Cookie`: 用户 Cookie（如果需要）

## 文件修改清单

### 已修改的文件
- `src/bilibili_extractor/modules/bilibili_api.py`
  - 移除了 `get_player_info()` 中的 WBI 签名
  - 直接使用原始 URL 请求

### 新增的诊断脚本
- `test_wbi_api_debug.py` - WBI API 诊断
- `test_cookie_and_ai_subtitle.py` - Cookie 和 AI 字幕 API 诊断

## 下一步建议

1. **立即**：验证 API 端点和 Cookie 的必要性
2. **短期**：修复 AI 字幕 API 的 404 问题
3. **中期**：添加 Cookie 验证和刷新机制
4. **长期**：考虑浏览器自动化作为备选方案

## 参考资源

- JS 版本代码：`docs/reference/SubBatch/background.js`
- 诊断脚本：`test_wbi_api_debug.py`, `test_cookie_and_ai_subtitle.py`
- 规划文件：`task_plan.md`, `findings.md`

## 结论

Python 版本的 AI 字幕获取问题主要由以下因素造成：
1. ✅ WBI 签名误用（已修复）
2. ⚠️ AI 字幕 API 返回 404（需要调查）
3. ⚠️ Cookie 不可用（用户需要提供）

通过解决这些问题，应该能够使 Python 版本的 AI 字幕获取功能正常工作。
