# B站字幕获取架构总结

## 概述

项目实现了一个完整的三级降级字幕获取系统，核心是 **WBI 签名算法** 的应用。该系统能够在 B站 API 风控触发时自动重试和降级，确保字幕获取的可靠性。

## 字幕获取流程

### 三级降级链路

```
┌─────────────────────────────────────────────────────────────┐
│                   SubtitleFetcher                           │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ 第一级：WBI API (/x/player/wbi/v2)                   │  │
│  │ ✓ 使用 WBI 签名（最安全）                             │  │
│  │ ✓ 支持智能重试（412 风控）                            │  │
│  │ ✓ 支持倒计时等待（20秒）                              │  │
│  │ ✓ 最多重试 3 次                                       │  │
│  │                                                      │  │
│  │ 失败原因：                                            │  │
│  │ - HTTP 412 风控错误（重试 3 次后仍失败）              │  │
│  │ - 网络错误                                            │  │
│  │ - API 返回错误码                                      │  │
│  └──────────────────────────────────────────────────────┘  │
│                          ↓                                  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ 第二级：V2 API (/x/player/v2)                        │  │
│  │ ✓ 无需签名（兼容性好）                                │  │
│  │ ✓ 字幕内容验证（aid/cid 匹配）                        │  │
│  │ ✓ 检测 AI 字幕混乱问题                                │  │
│  │                                                      │  │
│  │ 失败原因：                                            │  │
│  │ - 字幕 aid/cid 不匹配（AI 字幕混乱）                  │  │
│  │ - 字幕内容为空                                        │  │
│  │ - 网络错误                                            │  │
│  └──────────────────────────────────────────────────────┘  │
│                          ↓                                  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ 第三级：BBDown（最终保障）                            │  │
│  │ ✓ 第三方工具（独立实现）                              │  │
│  │ ✓ 不依赖 B站 API                                      │  │
│  │ ✓ 最后的救命稻草                                      │  │
│  │                                                      │  │
│  │ 失败原因：                                            │  │
│  │ - BBDown 工具不可用                                   │  │
│  │ - 视频无字幕                                          │  │
│  └──────────────────────────────────────────────────────┘  │
│                          ↓                                  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ 最终结果：SubtitleNotFoundError                       │  │
│  │ 所有方式都失败，无法获取字幕                          │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## WBI 签名机制

### 什么是 WBI 签名？

WBI（Web Browser Interface）签名是 B站为了防止 API 滥用而实现的安全机制。它通过以下步骤工作：

### WBI 签名流程

```
1. 获取 WBI 密钥
   ├─ 调用 /x/web-interface/nav API
   ├─ 提取 wbi_img.img_url 和 wbi_img.sub_url
   └─ 从 URL 中提取 img_key 和 sub_key（各 32 字符）

2. 生成 mixin_key
   ├─ 拼接：orig = img_key + sub_key（64 字符）
   ├─ 使用 MIXIN_KEY_ENC_TAB 重排
   └─ 取前 32 个字符作为 mixin_key

3. 构建签名参数
   ├─ 添加 wts（当前时间戳）
   ├─ 排序所有参数
   ├─ 过滤特殊字符 "!'()*"
   └─ URL 编码

4. 计算签名
   ├─ query = URL 编码后的参数
   ├─ w_rid = MD5(query + mixin_key)
   └─ 添加 w_rid 到请求参数

5. 发送请求
   └─ GET /x/player/wbi/v2?aid=xxx&cid=xxx&wts=xxx&w_rid=xxx
```

### MIXIN_KEY_ENC_TAB 编码表

这是一个 64 元素的排列表，用于打乱 `img_key + sub_key` 的字符顺序：

```python
MIXIN_KEY_ENC_TAB = [
    46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35, 27, 43, 5, 49,
    33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13, 37, 48, 7, 16, 24, 55, 40,
    61, 26, 17, 0, 1, 60, 51, 30, 4, 22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11,
    36, 20, 34, 44, 52
]
```

**工作原理**：
- 对于表中的每个索引 `i`，取 `orig[i]` 这个字符
- 按顺序拼接所有字符
- 取前 32 个字符作为 `mixin_key`

### 项目中的实现

**文件**：`src/bilibili_extractor/modules/wbi_sign.py`

```python
def get_mixin_key(orig: str) -> str:
    """对 imgKey 和 subKey 进行字符顺序打乱编码。"""
    return reduce(lambda s, i: s + orig[i], MIXIN_KEY_ENC_TAB, '')[:32]

def encode_wbi(params: Dict[str, Any], img_key: str, sub_key: str) -> Dict[str, Any]:
    """为请求参数进行 WBI 签名。"""
    # 1. 生成 mixin_key
    mixin_key = get_mixin_key(img_key + sub_key)
    
    # 2. 添加时间戳
    curr_time = round(time.time())
    params['wts'] = curr_time
    
    # 3. 排序参数
    params = dict(sorted(params.items()))
    
    # 4. 过滤特殊字符
    params = {
        k: ''.join(filter(lambda chr: chr not in "!'()*", str(v)))
        for k, v in params.items()
    }
    
    # 5. URL 编码
    query = urllib.parse.urlencode(params)
    
    # 6. 计算签名
    wbi_sign = hashlib.md5((query + mixin_key).encode()).hexdigest()
    
    # 7. 返回带签名的参数
    params['w_rid'] = wbi_sign
    return params
```

## 风控处理机制

### 412 风控错误

当 B站 API 检测到异常请求时，会返回 HTTP 412 状态码。项目的处理流程：

```
HTTP 412 响应
    ↓
抛出 RiskControlError 异常
    ↓
SubtitleFetcher 捕获异常
    ↓
执行智能重试机制
    ├─ 等待 20 秒
    ├─ 每 5 秒输出倒计时日志
    ├─ 最多重试 3 次
    └─ 重试失败后降级到 V2 API
```

### 关键配置项

```python
# 在 Config 类中定义
api_request_interval: int = 20      # API 请求间隔（秒）
api_retry_max_attempts: int = 3     # API 重试最大次数
api_retry_wait_time: int = 20       # API 重试等待时间（秒）
```

## 字幕验证机制

### V2 API 字幕验证

当使用 V2 API 获取字幕时，项目会验证返回的字幕是否与请求的视频匹配：

```python
def _validate_subtitle(
    self,
    subtitle_data: Dict[str, Any],
    expected_aid: int,
    expected_cid: int
) -> None:
    """验证字幕数据的 aid/cid 是否匹配。"""
    # 检查字幕数据是否包含 aid/cid
    if 'aid' not in subtitle_data or 'cid' not in subtitle_data:
        self.logger.warning("字幕数据缺少 aid/cid 信息，无法验证匹配性")
        return
    
    returned_aid = subtitle_data.get('aid')
    returned_cid = subtitle_data.get('cid')
    
    # 验证匹配性
    if returned_aid != expected_aid or returned_cid != expected_cid:
        raise SubtitleMismatchError(
            message=f"Subtitle mismatch: expected aid={expected_aid}, cid={expected_cid}, "
                   f"got aid={returned_aid}, cid={returned_cid}",
            requested_aid=expected_aid,
            requested_cid=expected_cid,
            returned_aid=returned_aid,
            returned_cid=returned_cid
        )
```

**验证目的**：
- 防止 AI 字幕混乱问题
- 确保返回的字幕与请求的视频一致
- 如果不匹配，立即降级到 BBDown

## 速率限制

### RateLimiter 类

```python
class RateLimiter:
    """速率限制器，确保 API 请求间隔。"""
    
    def __init__(self, min_interval: float = 20.0):
        """初始化速率限制器。
        
        Args:
            min_interval: 最小请求间隔（秒），默认 20 秒
        """
        self.min_interval = min_interval
        self.last_request_time = 0.0
    
    def wait_if_needed(self):
        """如果需要，等待以满足速率限制。"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.min_interval:
            wait_time = self.min_interval - time_since_last
            time.sleep(wait_time)
        
        self.last_request_time = time.time()
```

**作用**：
- 降低触发风控的概率
- 保护 B站 API 服务
- 可通过配置调整间隔

## 核心类和方法

### BilibiliAPI 类

**主要方法**：
- `get_video_info(bvid, page)` - 获取视频信息（aid、cid）
- `get_player_info(aid, cid)` - 获取播放器信息（字幕列表）
  - 优先使用 WBI API
  - 失败时自动降级到 V2 API
- `download_subtitle(subtitle_url)` - 下载字幕文件

### SubtitleFetcher 类

**主要方法**：
- `fetch_from_bilibili_api(bvid, url)` - 三级降级链路的入口
- `_fetch_from_wbi_api(aid, cid)` - WBI API 获取（支持重试）
- `_fetch_from_v2_api(aid, cid)` - V2 API 获取（支持验证）
- `_fetch_from_bbdown(bvid)` - BBDown 获取（最终降级）
- `_retry_with_wait(func, max_attempts, wait_time)` - 智能重试机制
- `_validate_subtitle(subtitle_data, expected_aid, expected_cid)` - 字幕验证

## 异常处理

### 自定义异常

1. **RiskControlError** - HTTP 412 风控错误
   - 包含：message、video_id、suggested_wait_time、request_url
   - 触发：WBI API 返回 412 状态码
   - 处理：智能重试机制

2. **SubtitleMismatchError** - 字幕不匹配错误
   - 包含：message、requested_aid、requested_cid、returned_aid、returned_cid
   - 触发：V2 API 返回的字幕 aid/cid 不匹配
   - 处理：降级到 BBDown

3. **SubtitleValidationError** - 字幕验证错误
   - 触发：字幕为空或格式不正确
   - 处理：触发降级机制

4. **SubtitleNotFoundError** - 字幕不存在错误
   - 触发：所有方式都失败
   - 处理：抛出异常，终止处理

## 日志级别规范

- **DEBUG** - 详细的调试信息（API 调用、缓存命中等）
- **INFO** - 正常的状态信息（开始使用某个 API、重试倒计时等）
- **WARNING** - 警告信息（风控触发、字幕不匹配、降级等）
- **ERROR** - 错误信息（最终失败、无法恢复的错误等）

## 配置示例

```yaml
# config/config.yaml
api_request_interval: 20      # API 请求间隔（秒）
api_retry_max_attempts: 3     # API 重试最大次数
api_retry_wait_time: 20       # API 重试等待时间（秒）
```

## 性能优化

### 缓存机制

- **LRU 缓存**：最多 100 条记录
- **TTL**：60 秒过期时间
- **缓存键**：`prefix:arg1_arg2_...`

### 连接池

- **连接数**：10
- **最大连接数**：10
- **自动重试**：500、502、503、504 状态码

## 总结

项目的字幕获取系统是一个**多层次、高可靠性**的解决方案：

1. **WBI 签名** - 安全、高效的 API 访问
2. **智能重试** - 自动处理风控错误
3. **字幕验证** - 防止 AI 字幕混乱
4. **三级降级** - 确保最终能获取字幕
5. **速率控制** - 降低风控触发概率
6. **详细日志** - 便于调试和监控

这个架构能够在各种网络和 API 条件下，可靠地获取 B站视频的字幕。
