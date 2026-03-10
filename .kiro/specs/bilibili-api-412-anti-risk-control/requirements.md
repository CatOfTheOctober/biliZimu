# 需求文档：B站 API 412 风控规避和字幕验证机制

## 简介

本功能旨在解决 B站 API 字幕获取时的两个关键问题：

1. **WBI API 风控问题**：`/x/player/wbi/v2` 接口有时会触发 412 风控错误
2. **V2 API 字幕错误问题**：降级到 `/x/player/v2` 接口时，返回的 AI 字幕可能与当前视频对不上

本功能将实现完整的 API 降级链路（WBI API → V2 API → BBDown），包括智能重试机制、字幕内容验证、请求速率控制和详细的状态追踪，确保获取正确的字幕内容。

## 术语表

- **BilibiliAPI**: B站 API 客户端类，负责与 B站服务器通信
- **SubtitleFetcher**: 字幕获取器，负责从多个来源获取字幕
- **WBI_API**: B站 WBI 签名接口 `/x/player/wbi/v2`，第一优先级字幕获取方式
- **V2_API**: B站旧版接口 `/x/player/v2`，第二优先级字幕获取方式（降级方案）
- **RiskControl**: B站的风控系统，用于检测和限制异常请求
- **RetryMechanism**: 重试机制，在请求失败时自动重试
- **RateLimiter**: 速率限制器，控制 API 请求频率
- **SubtitleValidator**: 字幕验证器，验证字幕内容是否匹配视频
- **SubtitleMismatchError**: 字幕不匹配异常，当字幕的 aid/cid 与请求不符时抛出
- **BBDown**: 第三方 B站视频下载工具，作为最终降级方案

## 需求

### 需求 1：检测 412 风控错误

**用户故事：** 作为系统，我需要检测 B站 API 返回的 412 风控错误，以便采取相应的处理措施。

#### 验收标准

1. WHEN BilibiliAPI 收到 HTTP 412 状态码响应，THEN THE BilibiliAPI SHALL 识别为风控错误
2. WHEN 检测到 412 风控错误，THEN THE BilibiliAPI SHALL 记录详细的错误日志（包括请求 URL、时间戳、视频 ID）
3. WHEN 检测到 412 风控错误，THEN THE BilibiliAPI SHALL 抛出自定义的 RiskControlError 异常
4. THE RiskControlError 异常 SHALL 包含错误消息、视频 ID 和建议的等待时间

### 需求 2：WBI API 智能重试机制

**用户故事：** 作为用户，当 WBI API 触发风控时，我希望系统能自动等待并重试，而不是直接降级。

#### 验收标准

1. WHEN SubtitleFetcher 捕获到 RiskControlError 异常，THEN THE RetryMechanism SHALL 等待 20 秒后重试 WBI_API
2. THE RetryMechanism SHALL 最多重试 WBI_API 3 次
3. WHEN WBI_API 重试次数达到上限，THEN THE SubtitleFetcher SHALL 降级到 V2_API
4. WHILE 等待重试期间，THE RetryMechanism SHALL 每 5 秒输出一次倒计时日志
5. WHEN WBI_API 重试成功获取字幕，THEN THE SubtitleFetcher SHALL 记录成功日志并返回字幕数据

### 需求 3：降级状态追踪

**用户故事：** 作为用户，我需要清楚了解系统当前使用的是哪个 API，以及为什么进行了降级。

#### 验收标准

1. WHEN 使用 WBI_API 获取字幕，THEN THE System SHALL 输出日志"正在使用 WBI API 获取字幕"
2. WHEN WBI_API 触发 412 风控，THEN THE System SHALL 输出警告"WBI API 触发风控（412），等待 20 秒后重试..."
3. WHILE 等待重试期间，THE System SHALL 每 5 秒输出倒计时消息"等待中... 剩余 X 秒"
4. WHEN 开始重试 WBI_API，THEN THE System SHALL 输出信息"正在进行第 X 次重试（WBI API）..."
5. WHEN WBI_API 重试成功，THEN THE System SHALL 输出成功消息"WBI API 重试成功，已获取字幕"
6. WHEN WBI_API 重试失败达到上限，THEN THE System SHALL 输出信息"WBI API 失败，降级到 V2 API"
7. WHEN 使用 V2_API 获取字幕，THEN THE System SHALL 输出日志"正在使用 V2 API 获取字幕"
8. WHEN V2_API 字幕验证失败，THEN THE System SHALL 输出警告"V2 API 返回的字幕与视频不匹配，降级到 BBDown"
9. WHEN 降级到 BBDown，THEN THE System SHALL 输出信息"API 方式失败，使用 BBDown 获取字幕"

### 需求 4：字幕基本验证

**用户故事：** 作为用户，我需要确保获取的字幕数据不为空且格式正确。

#### 验收标准

1. WHEN SubtitleFetcher 获取到字幕数据，THEN THE SubtitleValidator SHALL 验证字幕是否为空
2. WHEN 字幕数据为空，THEN THE SubtitleValidator SHALL 抛出 SubtitleValidationError 异常
3. WHEN 字幕数据格式不正确，THEN THE SubtitleValidator SHALL 抛出 SubtitleValidationError 异常
4. WHEN 字幕基本验证失败，THEN THE SubtitleFetcher SHALL 将此次获取视为失败并触发降级机制

### 需求 5：请求速率控制

**用户故事：** 作为系统，我需要控制 API 请求频率，降低触发风控的概率。

#### 验收标准

1. THE RateLimiter SHALL 确保两次 API 请求之间至少间隔 20 秒
2. WHEN BilibiliAPI 准备发送请求，THEN THE RateLimiter SHALL 检查距离上次请求的时间间隔
3. IF 时间间隔小于 20 秒，THEN THE RateLimiter SHALL 等待直到满足 20 秒间隔
4. THE RateLimiter SHALL 记录每次请求的时间戳
5. WHERE 配置文件指定了自定义请求间隔，THE RateLimiter SHALL 使用配置的间隔值

### 需求 6：API 降级链路

**用户故事：** 作为系统，我需要实现完整的 API 降级链路，确保在各种失败情况下都能尝试获取正确的字幕。

#### 验收标准

1. THE SubtitleFetcher SHALL 按照以下顺序尝试获取字幕：
   - 第一优先级：WBI_API (`/x/player/wbi/v2`)
   - 第二优先级：V2_API (`/x/player/v2`) + 字幕验证
   - 第三优先级：BBDown
2. WHEN WBI_API 返回 412，THEN THE SubtitleFetcher SHALL 等待 20 秒后重试 WBI_API（最多 3 次）
3. WHEN WBI_API 重试 3 次后仍失败，THEN THE SubtitleFetcher SHALL 降级到 V2_API
4. WHEN V2_API 返回字幕，THEN THE SubtitleFetcher SHALL 验证字幕内容
5. WHEN V2_API 字幕验证失败，THEN THE SubtitleFetcher SHALL 降级到 BBDown
6. WHEN BBDown 也失败，THEN THE SubtitleFetcher SHALL 返回 SubtitleNotFoundError

### 需求 7：配置管理

**用户故事：** 作为用户，我希望能够配置重试次数、等待时间和请求间隔等参数。

#### 验收标准

1. THE System SHALL 支持通过配置文件设置 `api_request_interval`（默认 20 秒）
2. THE System SHALL 支持通过配置文件设置 `api_retry_max_attempts`（默认 3 次）
3. THE System SHALL 支持通过配置文件设置 `api_retry_wait_time`（默认 20 秒）
4. WHEN 配置文件中未指定参数，THEN THE System SHALL 使用默认值
5. THE System SHALL 在启动时验证配置参数的有效性（正整数）

### 需求 8：错误日志记录

**用户故事：** 作为开发者，我需要详细的错误日志来分析和调试风控问题。

#### 验收标准

1. WHEN 触发 412 风控错误，THEN THE System SHALL 记录完整的请求信息（URL、headers、参数）
2. WHEN 触发 412 风控错误，THEN THE System SHALL 记录响应信息（状态码、响应体）
3. WHEN 重试失败，THEN THE System SHALL 记录每次重试的详细信息
4. THE System SHALL 使用 WARNING 级别记录风控错误
5. THE System SHALL 使用 ERROR 级别记录最终失败的情况

### 需求 9：V2 API 字幕验证

**用户故事：** 作为用户，当系统使用 V2 API 获取字幕时，我需要确保返回的字幕内容与当前视频匹配。

#### 验收标准

1. WHEN SubtitleFetcher 从 V2_API 获取字幕，THEN THE SubtitleValidator SHALL 验证字幕的 aid/cid 是否匹配请求的视频
2. WHEN 字幕数据中不包含 aid/cid 信息，THEN THE SubtitleValidator SHALL 记录警告日志"字幕数据缺少 aid/cid 信息，无法验证匹配性"
3. WHEN 字幕的 aid/cid 与请求不匹配，THEN THE SubtitleValidator SHALL 抛出 SubtitleMismatchError 异常
4. WHEN 字幕验证失败，THEN THE SubtitleFetcher SHALL 将此次获取标记为失败并触发降级到 BBDown
5. THE SubtitleValidator SHALL 在验证失败时记录详细信息（请求的 aid/cid、返回的 aid/cid）

### 需求 10：V2 API 降级处理

**用户故事：** 作为系统，当 WBI API 失败后，我需要尝试使用 V2 API 并验证返回的字幕。

#### 验收标准

1. WHEN WBI_API 重试 3 次失败后，THEN THE SubtitleFetcher SHALL 尝试使用 V2_API 获取字幕
2. WHEN 使用 V2_API 获取字幕，THEN THE SubtitleFetcher SHALL 记录信息日志"WBI API 失败，降级到 V2 API"
3. WHEN V2_API 成功返回字幕数据，THEN THE SubtitleFetcher SHALL 调用 SubtitleValidator 验证字幕
4. WHEN V2_API 字幕验证通过，THEN THE SubtitleFetcher SHALL 返回字幕数据
5. WHEN V2_API 字幕验证失败，THEN THE SubtitleFetcher SHALL 记录警告日志并降级到 BBDown
6. WHEN V2_API 请求失败（网络错误、超时等），THEN THE SubtitleFetcher SHALL 直接降级到 BBDown

### 需求 11：降级链路完整性

**用户故事：** 作为用户，我需要系统在所有 API 方式都失败时，能够使用 BBDown 作为最终保障。

#### 验收标准

1. WHEN WBI_API 和 V2_API 都失败，THEN THE SubtitleFetcher SHALL 使用 BBDown 获取字幕
2. WHEN 降级到 BBDown，THEN THE SubtitleFetcher SHALL 记录信息日志"API 方式失败，使用 BBDown 获取字幕"
3. WHEN BBDown 成功获取字幕，THEN THE SubtitleFetcher SHALL 返回字幕数据
4. WHEN BBDown 也失败，THEN THE SubtitleFetcher SHALL 抛出 SubtitleNotFoundError 异常
5. THE SubtitleFetcher SHALL 在最终失败时记录完整的降级链路日志（WBI API → V2 API → BBDown 的失败原因）
