# 完整流程分析：JS版本 vs Python版本

## 目标
通过分析 `background.js` 中的完整消息处理函数，梳理完整的字幕下载流程，找出 Python 版本的真实错误。

---

## 第一部分：JS版本的完整流程

### 1. 初始化阶段（第1-15行）

```javascript
// 全局变量声明
let bilibiliCookie = '';

// 在扩展启动时从localStorage读取Cookie
chrome.storage.local.get(['bilibiliCookie'], function (result) {
  if (result.bilibiliCookie) {
    bilibiliCookie = result.bilibiliCookie;
    console.log('从存储中加载Cookie (部分显示):', bilibiliCookie.substring(0, 20) + '...');
  } else {
    console.log('存储中没有找到Cookie');
  }
});
```

**关键点**：
- Cookie 是全局变量，在扩展启动时初始化
- 从 `chrome.storage.local` 读取持久化的 Cookie
- 支持动态更新

### 2. 消息处理函数（第944行）

```javascript
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  // 处理多种消息类型
  if (message.action === 'updateCookie' || message.action === 'setCookie') { ... }
  if (message.type === 'FILE_CHANGED') { ... }
  if (message.action === 'getTabUrl') { ... }
  if (message.action === 'fetchBilibiliInfo') { ... }
  if (message.action === 'fetchBilibiliSubtitle') { ... }
  if (message.action === 'getCookie') { ... }
  if (message.action === 'testWbiApi') { ... }
  if (message.action === 'fetchCollectionList') { ... }
});
```

**关键消息类型**：

#### 2.1 `fetchBilibiliInfo` - 获取视频信息
```javascript
if (message.action === 'fetchBilibiliInfo') {
  getBilibiliVideoInfo(message.videoId)
    .then((result) => {
      sendResponse(result);
    })
    .catch((error) => {
      console.error('获取B站视频信息出错:', error);
      sendResponse({
        success: false,
        message: error.message || '网络请求错误',
      });
    });
  return true;
}
```

**作用**：获取视频的基本信息，包括 **aid**（视频ID）

#### 2.2 `fetchBilibiliSubtitle` - 获取字幕
```javascript
if (message.action === 'fetchBilibiliSubtitle') {
  console.log('收到获取字幕请求:', message);
  if (!message.cid) {
    console.error('获取字幕请求缺少必要参数 cid');
    sendResponse({
      success: false,
      message: '缺少必要参数cid，请确保已获取视频信息',
    });
    return true;
  }

  if (message.bvid) {
    console.log('仅使用bvid方式获取字幕');
    getBilibiliSubtitle(message.cid, message.bvid)
      .then((result) => {
        console.log('字幕获取结果:', result);
        sendResponse(result);
      })
      .catch((error) => {
        console.error('获取B站视频字幕出错:', error);
        sendResponse({
          success: false,
          message: error.message || '网络请求错误',
          error: '使用bvid获取字幕失败',
        });
      });
  }
  return true;
}
```

**关键参数**：
- `cid` - 视频分P的ID（必需）
- `bvid` - 视频的BV号（必需）
- `aid` - 视频的AV号（可选，但优先使用）

### 3. 核心函数：`getBilibiliSubtitle(cid, bvid, retryCount = 2)`

#### 3.1 第一步：获取 aid
```javascript
// 首先获取视频的基本信息，确保有aid
let aid;
try {
  const viewInfo = await fetchWithHeaders(`https://api.bilibili.com/x/web-interface/view?bvid=${bvid}`);
  if (viewInfo.code === 0 && viewInfo.data) {
    aid = viewInfo.data.aid;
    console.log('成功获取aid:', aid);
  } else {
    console.error('获取视频信息失败:', viewInfo);
  }
} catch (error) {
  console.error('获取视频基本信息出错:', error);
}
```

**重要发现**：
- 即使已经有 `bvid`，JS 版本仍然会调用 `/x/web-interface/view?bvid=` 来获取 `aid`
- 这是因为某些 API 端点需要 `aid` 而不是 `bvid`

#### 3.2 第二步：构建字幕信息请求 URL
```javascript
// 构建字幕信息请求URL - 优先使用aid+cid的组合
let subtitleInfoUrl;
if (aid) {
  subtitleInfoUrl = `https://api.bilibili.com/x/player/wbi/v2?aid=${aid}&cid=${cid}`;
} else {
  subtitleInfoUrl = `https://api.bilibili.com/x/player/v2?cid=${cid}&bvid=${bvid}`;
}

console.log('字幕信息请求URL:', subtitleInfoUrl);
```

**关键发现**：
- **优先使用 `aid+cid` 调用 `/x/player/wbi/v2`**
- 如果没有 `aid`，才使用 `/x/player/v2?cid=&bvid=`
- 这说明 `/x/player/wbi/v2` 是首选接口

#### 3.3 第三步：获取字幕信息
```javascript
const subtitleInfoData = await fetchWithHeaders(subtitleInfoUrl);
console.log('字幕信息响应代码:', subtitleInfoData.code);

if (subtitleInfoData.code !== 0 || !subtitleInfoData.data) {
  console.error('获取字幕信息失败:', subtitleInfoData);
  throw new Error('获取字幕信息失败: ' + (subtitleInfoData.message || '未知错误'));
}

// 完整记录字幕数据，便于调试
console.log('完整字幕信息数据:', JSON.stringify(subtitleInfoData.data));
```

#### 3.4 第四步：检查字幕列表
```javascript
// 检查是否有字幕
if (!subtitleInfoData.data.subtitle) {
  console.log('API响应中不包含subtitle字段');
  return {
    success: false,
    message: '该视频没有字幕或字幕数据为空',
  };
}

const subtitles = subtitleInfoData.data.subtitle.subtitles || [];
console.log('找到字幕列表数量:', subtitles.length);

if (subtitles.length === 0) {
  console.log('字幕列表为空');
  return {
    success: false,
    message: '该视频没有可用字幕',
  };
}
```

#### 3.5 第五步：查找 AI 字幕
```javascript
// 获取第一个字幕（通常是默认字幕），优先获取中文字幕
const defaultSubtitle = subtitles.find((item) => item.lan === 'ai-zh');
console.log('默认字幕信息:', defaultSubtitle);

const subtitleUrl = defaultSubtitle.subtitle_url;
```

**关键发现**：
- 优先查找 `lan === 'ai-zh'` 的字幕（AI 生成的中文字幕）
- 如果找到，使用其 `subtitle_url`

#### 3.6 第六步：处理 AI 字幕 URL 为空的情况
```javascript
if (!subtitleUrl) {
  console.log('字幕URL为空');

  // 检查是否是自动生成字幕（AI字幕）
  if (defaultSubtitle.lan && defaultSubtitle.lan.startsWith('ai-')) {
    console.log('检测到自动生成的AI字幕，但URL为空，需要再次请求获取字幕URL');

    // 对于自动生成的字幕，需要通过另一个API获取实际的字幕URL
    try {
      const aiSubtitleUrl = `https://api.bilibili.com/x/player/v2/ai/subtitle/search/stat?aid=${aid}&cid=${cid}`;
      console.log('请求AI字幕URL:', aiSubtitleUrl);

      const aiSubtitleData = await fetchWithHeaders(aiSubtitleUrl);

      if (aiSubtitleData.code === 0 && aiSubtitleData.data && aiSubtitleData.data.subtitle_url) {
        // 找到了AI字幕的URL
        const fullAiSubtitleUrl = formatSubtitleUrl(aiSubtitleData.data.subtitle_url);
        console.log('成功获取AI字幕URL:', fullAiSubtitleUrl);
        // ... 继续处理
      }
    } catch (aiUrlError) {
      console.error('获取AI字幕URL失败:', aiUrlError);
      return {
        success: false,
        message: '获取自动生成字幕失败: ' + (aiUrlError.message || '未知错误'),
      };
    }
  }
}
```

**关键发现**：
- 如果 AI 字幕的 `subtitle_url` 为空，需要调用 `/x/player/v2/ai/subtitle/search/stat?aid=&cid=`
- 这个 API 需要 `aid` 和 `cid` 参数
- 这个 API 可能需要 Cookie

### 4. 请求头处理函数：`fetchWithHeaders(url)`

```javascript
async function fetchWithHeaders(url) {
  try {
    console.log('发起API请求:', url);
    logCookieStatus(); // 添加Cookie日志记录

    // 添加Cookie诊断
    if (url.includes('api.bilibili.com')) {
      console.log('检测到B站API请求，执行Cookie诊断');
      diagnoseCookie();
    }

    // 检查是否是WBI接口
    const isWbiRequest = url.includes('/x/player/wbi/v2');

    const headers = {
      'User-Agent':
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
      Accept: 'application/json, text/plain, */*',
      'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
      Origin: 'https://www.bilibili.com',
      Referer: 'https://www.bilibili.com/',
      'Cache-Control': 'no-cache',
      Connection: 'keep-alive',
      Pragma: 'no-cache',
      'X-Wbi-UA': 'Win32.Chrome.109.0.0.0',
    };

    // 如果有Cookie，添加到请求头中
    if (bilibiliCookie && bilibiliCookie.trim() !== '') {
      headers['Cookie'] = bilibiliCookie;
      console.log('请求已添加Cookie (部分显示):', bilibiliCookie.substring(0, 20) + '...');
    } else {
      console.log('请求未添加Cookie，因为Cookie未设置或为空');
      // 尝试再次从storage获取Cookie
      try {
        const result = await chrome.storage.local.get(['bilibiliCookie']);
        if (result.bilibiliCookie && result.bilibiliCookie.trim() !== '') {
          bilibiliCookie = result.bilibiliCookie;
          headers['Cookie'] = bilibiliCookie;
          console.log('从storage重新获取Cookie并添加到请求头 (部分显示):', bilibiliCookie.substring(0, 20) + '...');
        }
      } catch (storageError) {
        console.error('从storage获取Cookie失败:', storageError);
      }
    }

    // 如果是WBI请求，需要特殊处理
    if (isWbiRequest) {
      console.log('检测到WBI接口请求，进行特殊处理');
      return await fetchWbiRequest(url, headers);
    }

    console.log('发送请求前的完整Headers:', JSON.stringify(headers));

    const response = await fetch(url, {
      method: 'GET',
      headers: headers,
      credentials: 'include', // 修改为include以确保Cookie被发送
    });

    if (!response.ok) {
      console.error(`API请求失败: ${url}, 状态码: ${response.status}`);
      throw new Error(`请求失败，状态码: ${response.status}`);
    }

    const data = await response.json();
    console.log('API请求响应:', data);
    return data;
  } catch (error) {
    console.error('API请求出错:', error);
    throw error;
  }
}
```

**关键发现**：
- 所有请求都添加了完整的浏览器标识头
- 包括 `X-Wbi-UA: Win32.Chrome.109.0.0.0`
- Cookie 是可选的，但如果存在则添加
- 对 WBI 请求进行特殊处理

---

## 第二部分：Python 版本的问题

### 问题 1：缺少 `aid` 获取步骤
**JS 版本**：
```javascript
// 首先获取视频的基本信息，确保有aid
const viewInfo = await fetchWithHeaders(`https://api.bilibili.com/x/web-interface/view?bvid=${bvid}`);
aid = viewInfo.data.aid;
```

**Python 版本**：
- 没有调用 `/x/web-interface/view?bvid=` 来获取 `aid`
- 直接使用 `bvid` 调用 `/x/player/v2`

**影响**：
- 某些 API 端点（如 `/x/player/v2/ai/subtitle/search/stat`）需要 `aid`
- 没有 `aid` 可能导致某些请求失败

### 问题 2：AI 字幕 URL 为空的处理
**JS 版本**：
```javascript
if (!subtitleUrl) {
  if (defaultSubtitle.lan && defaultSubtitle.lan.startsWith('ai-')) {
    // 调用 /x/player/v2/ai/subtitle/search/stat 获取 AI 字幕 URL
    const aiSubtitleUrl = `https://api.bilibili.com/x/player/v2/ai/subtitle/search/stat?aid=${aid}&cid=${cid}`;
    const aiSubtitleData = await fetchWithHeaders(aiSubtitleUrl);
    // 处理响应
  }
}
```

**Python 版本**：
- 可能没有正确处理 AI 字幕 URL 为空的情况
- 可能没有调用 `/x/player/v2/ai/subtitle/search/stat`

### 问题 3：Cookie 管理
**JS 版本**：
- 全局变量 `bilibiliCookie` 在启动时初始化
- 支持动态更新
- 每次请求时检查 Cookie 是否存在
- 如果不存在，尝试从 `chrome.storage.local` 重新获取

**Python 版本**：
- Cookie 管理可能不完善
- 可能没有正确处理 Cookie 不存在的情况

---

## 第三部分：关键发现总结

### 1. 完整的字幕获取流程（5 步）
1. **获取 aid**：调用 `/x/web-interface/view?bvid=` 获取视频的 `aid`
2. **获取字幕信息**：调用 `/x/player/wbi/v2?aid=&cid=` 获取字幕列表
3. **查找 AI 字幕**：在字幕列表中查找 `lan === 'ai-zh'` 的字幕
4. **获取字幕 URL**：如果 AI 字幕 URL 为空，调用 `/x/player/v2/ai/subtitle/search/stat?aid=&cid=`
5. **获取字幕内容**：调用字幕 URL 获取实际的字幕内容

### 2. 关键参数
- **aid**：视频的 AV 号（从 `/x/web-interface/view?bvid=` 获取）
- **bvid**：视频的 BV 号（用户提供）
- **cid**：视频分P的 ID（用户提供）

### 3. 关键 API 端点
- `/x/web-interface/view?bvid=` - 获取视频信息（包括 aid）
- `/x/player/wbi/v2?aid=&cid=` - 获取字幕列表（优先使用）
- `/x/player/v2?cid=&bvid=` - 获取字幕列表（备选）
- `/x/player/v2/ai/subtitle/search/stat?aid=&cid=` - 获取 AI 字幕 URL

### 4. 关键请求头
- `User-Agent`: 浏览器标识
- `Accept`: `application/json, text/plain, */*`
- `Accept-Language`: `zh-CN,zh;q=0.9,en;q=0.8`
- `X-Wbi-UA`: `Win32.Chrome.109.0.0.0`
- `Cookie`: 用户的 B 站 Cookie（可选但重要）

### 5. Cookie 的作用
- 用于身份验证
- 某些 API 端点（如 `/x/player/v2/ai/subtitle/search/stat`）可能需要 Cookie
- 没有 Cookie 可能导致 404 或其他错误

---

## 第四部分：Python 版本的改进方案

### 改进 1：添加 `aid` 获取步骤
```python
def get_player_info(self, bvid: str, cid: str) -> dict:
    """获取播放器信息，包括字幕列表"""
    # 第一步：获取 aid
    view_url = f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}"
    view_response = self.session.get(view_url, headers=self.headers)
    view_data = view_response.json()
    
    if view_data.get('code') != 0:
        raise Exception(f"获取视频信息失败: {view_data.get('message')}")
    
    aid = view_data['data']['aid']
    
    # 第二步：使用 aid+cid 获取字幕信息
    player_url = f"https://api.bilibili.com/x/player/wbi/v2?aid={aid}&cid={cid}"
    player_response = self.session.get(player_url, headers=self.headers)
    return player_response.json()
```

### 改进 2：处理 AI 字幕 URL 为空的情况
```python
def get_ai_subtitle_url(self, aid: str, cid: str) -> str:
    """获取 AI 字幕的实际 URL"""
    ai_url = f"https://api.bilibili.com/x/player/v2/ai/subtitle/search/stat?aid={aid}&cid={cid}"
    response = self.session.get(ai_url, headers=self.headers)
    data = response.json()
    
    if data.get('code') != 0:
        raise Exception(f"获取 AI 字幕 URL 失败: {data.get('message')}")
    
    return data['data']['subtitle_url']
```

### 改进 3：完整的字幕获取流程
```python
def get_subtitle_with_ai_fallback(self, bvid: str, cid: str) -> dict:
    """完整的字幕获取流程，包括 AI 字幕处理"""
    # 第一步：获取 aid
    aid = self.get_aid_from_bvid(bvid)
    
    # 第二步：获取字幕信息
    player_info = self.get_player_info(bvid, cid)
    
    # 第三步：查找 AI 字幕
    subtitles = player_info['data']['subtitle']['subtitles']
    ai_subtitle = next((s for s in subtitles if s['lan'] == 'ai-zh'), None)
    
    if not ai_subtitle:
        # 没有 AI 字幕，使用其他字幕
        return self.get_subtitle_content(subtitles[0]['subtitle_url'])
    
    # 第四步：获取 AI 字幕 URL
    if not ai_subtitle.get('subtitle_url'):
        ai_subtitle_url = self.get_ai_subtitle_url(aid, cid)
    else:
        ai_subtitle_url = ai_subtitle['subtitle_url']
    
    # 第五步：获取字幕内容
    return self.get_subtitle_content(ai_subtitle_url)
```

---

## 总结

通过分析 JS 版本的完整流程，我们发现了 Python 版本的关键问题：

1. **缺少 `aid` 获取步骤** - 需要先调用 `/x/web-interface/view?bvid=` 获取 `aid`
2. **AI 字幕 URL 为空的处理不完善** - 需要调用 `/x/player/v2/ai/subtitle/search/stat?aid=&cid=`
3. **Cookie 管理不完善** - 需要确保 Cookie 被正确传递
4. **请求头不完整** - 需要添加所有必需的浏览器标识头

这些改进将使 Python 版本与 JS 版本保持一致，提高字幕获取的稳定性和成功率。
