# WBI 签名完整追踪分析

## 概述

通过追踪 JS 代码中 `fetchWithHeaders` 和 `encWbi` 函数的调用链，我们可以完全理解 WBI 签名的使用逻辑。

## 关键发现

### 1. WBI 签名的使用场景

**只有一个地方使用 WBI 签名**：
- 位置：第 1682 行
- 接口：`/x/space/wbi/arc/search`
- 用途：获取用户主页的视频列表

**不使用 WBI 签名的接口**：
- `/x/web-interface/view` - 获取视频信息
- `/x/player/wbi/v2` - 获取播放器信息（包含字幕）
- `/x/player/v2/ai/subtitle/search/stat` - 获取 AI 字幕 URL
- `/x/player/pagelist` - 获取视频分 P 列表

### 2. fetchWithHeaders 函数的调用链

```
fetchWithHeaders(url)
├── 调用 1: 获取视频信息
│   └── /x/web-interface/view?bvid=xxx
│       └── 不需要 WBI 签名
│
├── 调用 2: 获取播放器信息（字幕）
│   └── /x/player/wbi/v2?aid=xxx&cid=xxx
│       └── 不需要 WBI 签名（虽然 URL 中有 wbi）
│
├── 调用 3: 获取 AI 字幕 URL
│   └── /x/player/v2/ai/subtitle/search/stat?aid=xxx&cid=xxx
│       └── 不需要 WBI 签名
│
├── 调用 4: 获取用户视频列表（使用 WBI 签名）
│   └── /x/space/wbi/arc/search?...
│       └── 需要 WBI 签名 ✅
│
└── 调用 5: 获取视频分 P 列表
    └── /x/player/pagelist?bvid=xxx
        └── 不需要 WBI 签名
```

## 详细的 WBI 签名流程

### 步骤 1: 获取 WBI 密钥

```javascript
const wbiKeys = await getWbiKeys();
// 返回: { img_key: "xxx", sub_key: "xxx" }
```

**函数位置**：第 239 行
**调用接口**：`/x/web-interface/nav`
**返回数据**：
```javascript
{
  data: {
    wbi_img: {
      img_url: "https://i0.hdslb.com/bfs/wbi/xxx.png",
      sub_url: "https://i0.hdslb.com/bfs/wbi/xxx.png"
    }
  }
}
```

### 步骤 2: 准备请求参数

```javascript
const params = {
  mid: message.mid,           // 用户 ID
  pn: page,                   // 页码
  ps: pageSize,               // 每页数量
  tid: 0,
  keyword: '',
  order: 'pubdate',
  web_location: 1550101,
  order_avoided: true,
};
```

### 步骤 3: 计算 WBI 签名

```javascript
const query = encWbi(params, wbiKeys.img_key, wbiKeys.sub_key);
// 返回: "mid=xxx&pn=1&ps=30&...&wts=1234567890&w_rid=xxxxx"
```

**encWbi 函数的工作流程**：
1. 生成 mixin_key：`getMixinKey(img_key + sub_key)`
2. 添加时间戳：`params.wts = Math.round(Date.now() / 1000)`
3. 按 key 排序参数
4. 过滤特殊字符：`!'()*`
5. URL 编码参数
6. 计算 MD5 签名：`md5(query + mixin_key)`
7. 添加签名到参数：`w_rid=xxxxx`

### 步骤 4: 构建完整 URL

```javascript
const url = `https://api.bilibili.com/x/space/wbi/arc/search?${query}`;
// 例如: https://api.bilibili.com/x/space/wbi/arc/search?mid=123&pn=1&ps=30&...&wts=1234567890&w_rid=xxxxx
```

### 步骤 5: 发起请求

```javascript
const result = await fetchWithHeaders(url);
```

**fetchWithHeaders 函数的处理**：
1. 检查是否是 WBI 接口（`/x/player/wbi/v2`）
2. 如果是，调用 `fetchWbiRequest(url, headers)`
3. 如果不是，直接发起 fetch 请求
4. 添加 Cookie（如果有）
5. 返回 JSON 响应

## 关键区别

### `/x/player/wbi/v2` vs `/x/space/wbi/arc/search`

| 特性 | `/x/player/wbi/v2` | `/x/space/wbi/arc/search` |
|------|-------------------|-------------------------|
| 需要 WBI 签名 | ❌ 否 | ✅ 是 |
| 需要 Cookie | ❌ 否 | ❌ 否 |
| 用途 | 获取播放器信息（字幕） | 获取用户视频列表 |
| 参数 | aid, cid | mid, pn, ps, 等 |
| 返回数据 | 字幕列表 | 视频列表 |

## Python 版本的错误

Python 版本错误地对 `/x/player/wbi/v2` 进行了 WBI 签名，这是不必要的。

**错误的代码**：
```python
# 错误：对 /x/player/wbi/v2 进行 WBI 签名
params = {'aid': aid, 'cid': cid}
signed_params = encode_wbi(params, img_key, sub_key)
url = f"https://api.bilibili.com/x/player/wbi/v2?{query_string}"
```

**正确的代码**：
```python
# 正确：直接使用原始 URL，不进行签名
url = f"https://api.bilibili.com/x/player/wbi/v2?aid={aid}&cid={cid}"
```

## WBI 签名算法详解

### getMixinKey 函数

```javascript
function getMixinKey(orig) {
  let temp = '';
  mixinKeyEncTab.forEach((n) => {
    temp += orig[n];
  });
  return temp.slice(0, 32);
}
```

**工作原理**：
1. 输入：`img_key + sub_key`（64 个字符）
2. 使用 `mixinKeyEncTab` 重排映射表重新排列字符
3. 取前 32 个字符作为 mixin_key

**例子**：
```
输入: "7cd084941338484aae1ad9425b84077c4932caff0ff746eab6f01bf08b70ac45"
输出: "xxxxx" (32 个字符)
```

### encWbi 函数

```javascript
function encWbi(params, img_key, sub_key) {
  const mixin_key = getMixinKey(img_key + sub_key);
  const curr_time = Math.round(Date.now() / 1000);
  const chr_filter = /[!'()*]/g;
  
  // 1. 添加时间戳
  Object.assign(params, { wts: curr_time });
  
  // 2. 按 key 排序
  const query = Object.keys(params)
    .sort()
    .map((key) => {
      // 3. 过滤特殊字符
      const value = params[key].toString().replace(chr_filter, '');
      // 4. URL 编码
      return `${encodeURIComponent(key)}=${encodeURIComponent(value)}`;
    })
    .join('&');
  
  // 5. 计算签名
  const wbi_sign = md5(query + mixin_key);
  
  // 6. 返回带签名的查询字符串
  return query + '&w_rid=' + wbi_sign;
}
```

## 调用流程图

```
用户请求获取视频列表
    ↓
检查是否需要 WBI 签名
    ↓
是 → 获取 WBI 密钥 → 准备参数 → 计算签名 → 构建 URL → 发起请求
    ↓
否 → 直接构建 URL → 发起请求
    ↓
返回结果
```

## 总结

### WBI 签名的使用规则

1. **只有 `/x/space/wbi/arc/search` 需要 WBI 签名**
2. **其他 `/x/player/wbi/v2` 等接口不需要 WBI 签名**
3. **WBI 签名的目的是防止 API 滥用**
4. **签名包含时间戳，每次请求都会变化**

### Python 版本的修复

- ✅ 移除了对 `/x/player/wbi/v2` 的 WBI 签名
- ✅ 保留了 WBI 签名的实现（用于其他接口）
- ✅ 直接使用原始 URL 请求播放器信息

### 关键代码位置

| 功能 | 位置 | 行号 |
|------|------|------|
| getMixinKey | background.js | 第 213 行 |
| encWbi | background.js | 第 220 行 |
| getWbiKeys | background.js | 第 239 行 |
| fetchWithHeaders | background.js | 第 350 行 |
| fetchWbiRequest | background.js | 第 425 行 |
| 使用 WBI 签名 | background.js | 第 1682 行 |

## 参考资源

- WBI 签名文档：https://xtcqinghe.github.io/bac/docs/misc/sign/wbi.html
- B 站 API 参考：https://github.com/SocialSisterYi/bilibili-API-collect
- SubBatch 源代码：`docs/reference/SubBatch/background.js`
