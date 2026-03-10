# Python 版本改进方案

## 目标
基于 JS 版本的完整流程分析，系统地改进 Python 版本的字幕获取功能，使其与 JS 版本保持一致。

---

## 第一部分：问题诊断

### 问题 1：缺少 `aid` 获取步骤 ⚠️

**JS 版本的做法**：
```javascript
// 首先获取视频的基本信息，确保有aid
const viewInfo = await fetchWithHeaders(`https://api.bilibili.com/x/web-interface/view?bvid=${bvid}`);
aid = viewInfo.data.aid;
```

**Python 版本的问题**：
- 当前代码直接使用 `bvid` 调用 `/x/player/v2`
- 没有先调用 `/x/web-interface/view?bvid=` 获取 `aid`
- 这导致某些 API 端点（如 `/x/player/v2/ai/subtitle/search/stat`）无法正常工作

**影响**：
- AI 字幕 URL 为空时，无法调用 `/x/player/v2/ai/subtitle/search/stat?aid=&cid=` 获取 URL
- 因为没有 `aid` 参数

### 问题 2：AI 字幕 URL 为空的处理不完善 ⚠️

**JS 版本的做法**：
```javascript
if (!subtitleUrl) {
  if (defaultSubtitle.lan && defaultSubtitle.lan.startsWith('ai-')) {
    // 调用 /x/player/v2/ai/subtitle/search/stat 获取 AI 字幕 URL
    const aiSubtitleUrl = `https://api.bilibili.com/x/player/v2/ai/subtitle/search/stat?aid=${aid}&cid=${cid}`;
    const aiSubtitleData = await fetchWithHeaders(aiSubtitleUrl);
    
    if (aiSubtitleData.code === 0 && aiSubtitleData.data && aiSubtitleData.data.subtitle_url) {
      const fullAiSubtitleUrl = formatSubtitleUrl(aiSubtitleData.data.subtitle_url);
      // 继续处理字幕内容
    }
  }
}
```

**Python 版本的问题**：
- 可能没有检查 `subtitle_url` 是否为空
- 可能没有调用 `/x/player/v2/ai/subtitle/search/stat` 来获取 AI 字幕 URL
- 这导致 AI 字幕获取失败

### 问题 3：Cookie 管理不完善 ⚠️

**JS 版本的做法**：
```javascript
// 全局变量
let bilibiliCookie = '';

// 启动时从 chrome.storage.local 读取
chrome.storage.local.get(['bilibiliCookie'], function (result) {
  if (result.bilibiliCookie) {
    bilibiliCookie = result.bilibiliCookie;
  }
});

// 每次请求时检查
if (bilibiliCookie && bilibiliCookie.trim() !== '') {
  headers['Cookie'] = bilibiliCookie;
} else {
  // 尝试从 storage 重新获取
  const result = await chrome.storage.local.get(['bilibiliCookie']);
  if (result.bilibiliCookie && result.bilibiliCookie.trim() !== '') {
    bilibiliCookie = result.bilibiliCookie;
    headers['Cookie'] = bilibiliCookie;
  }
}
```

**Python 版本的问题**：
- Cookie 管理可能不够灵活
- 可能没有正确处理 Cookie 不存在的情况
- 可能没有在每次请求时检查 Cookie

### 问题 5：缺少 WBI 请求的特殊处理逻辑 ⚠️

**JS 版本的做法**：
```javascript
// fetchWithHeaders 中的逻辑
const isWbiRequest = url.includes('/x/player/wbi/v2');
if (isWbiRequest) {
  console.log('检测到WBI接口请求，进行特殊处理');
  return await fetchWbiRequest(url, headers);
}

// fetchWbiRequest 的特殊处理
async function fetchWbiRequest(url, headers) {
  // 1. 详细的响应日志
  // 2. 字幕数据特殊解析
  // 3. 错误重试机制（添加 isGaiaAvoided=false）
  // 4. 确保 Cookie 发送
}
```

**Python 版本的问题**：
- 没有对 `/x/player/wbi/v2` 进行特殊处理
- 缺少详细的响应日志
- 缺少错误重试机制
- 可能没有正确处理某些参数

**影响**：
- 某些请求可能因为缺少参数而失败
- 错误诊断困难
- 稳定性降低

**JS 版本的请求头**：
```javascript
const headers = {
  'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
  Accept: 'application/json, text/plain, */*',
  'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
  Origin: 'https://www.bilibili.com',
  Referer: 'https://www.bilibili.com/',
  'Cache-Control': 'no-cache',
  Connection: 'keep-alive',
  Pragma: 'no-cache',
  'X-Wbi-UA': 'Win32.Chrome.109.0.0.0',
};
```

**Python 版本的问题**：
- 可能缺少某些关键请求头
- 特别是 `X-Wbi-UA` 这个头可能没有添加

---

## 第二部分：改进方案

### 改进 1：添加 `aid` 获取函数

**新增函数**：`get_aid_from_bvid(bvid: str) -> str`

```python
def get_aid_from_bvid(self, bvid: str) -> str:
    """
    从 bvid 获取 aid（视频ID）
    
    Args:
        bvid: 视频的 BV 号
        
    Returns:
        aid: 视频的 AV 号
        
    Raises:
        Exception: 如果获取失败
    """
    url = f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}"
    
    try:
        response = self.session.get(url, headers=self.headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data.get('code') != 0:
            raise Exception(f"获取视频信息失败: {data.get('message', '未知错误')}")
        
        aid = data['data']['aid']
        logger.info(f"成功获取 aid: {aid}")
        return aid
        
    except Exception as e:
        logger.error(f"获取 aid 失败: {str(e)}")
        raise
```

### 改进 2：改进 `get_player_info` 函数

**修改前**：
```python
def get_player_info(self, bvid: str, cid: str) -> dict:
    """获取播放器信息"""
    url = f"https://api.bilibili.com/x/player/v2?cid={cid}&bvid={bvid}"
    response = self.session.get(url, headers=self.headers)
    return response.json()
```

**修改后**：
```python
def get_player_info(self, bvid: str, cid: str) -> dict:
    """
    获取播放器信息，包括字幕列表
    
    优先使用 aid+cid 调用 /x/player/wbi/v2，如果失败则使用 /x/player/v2
    
    Args:
        bvid: 视频的 BV 号
        cid: 视频分P的 ID
        
    Returns:
        dict: 播放器信息，包括字幕列表
    """
    # 第一步：获取 aid
    try:
        aid = self.get_aid_from_bvid(bvid)
    except Exception as e:
        logger.warning(f"获取 aid 失败，将使用 bvid 方式: {str(e)}")
        aid = None
    
    # 第二步：优先使用 aid+cid 调用 /x/player/wbi/v2
    if aid:
        url = f"https://api.bilibili.com/x/player/wbi/v2?aid={aid}&cid={cid}"
        logger.info(f"使用 aid+cid 方式获取字幕信息: {url}")
    else:
        url = f"https://api.bilibili.com/x/player/v2?cid={cid}&bvid={bvid}"
        logger.info(f"使用 bvid 方式获取字幕信息: {url}")
    
    try:
        response = self.session.get(url, headers=self.headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data.get('code') != 0:
            raise Exception(f"获取字幕信息失败: {data.get('message', '未知错误')}")
        
        logger.info("成功获取字幕信息")
        return data
        
    except Exception as e:
        logger.error(f"获取字幕信息失败: {str(e)}")
        raise
```

### 改进 3：新增 AI 字幕 URL 获取函数

**新增函数**：`get_ai_subtitle_url(aid: str, cid: str) -> str`

```python
def get_ai_subtitle_url(self, aid: str, cid: str) -> str:
    """
    获取 AI 字幕的实际 URL
    
    当 AI 字幕的 subtitle_url 为空时，需要调用此 API 获取实际的字幕 URL
    
    Args:
        aid: 视频的 AV 号
        cid: 视频分P的 ID
        
    Returns:
        str: AI 字幕的 URL
        
    Raises:
        Exception: 如果获取失败
    """
    url = f"https://api.bilibili.com/x/player/v2/ai/subtitle/search/stat?aid={aid}&cid={cid}"
    
    try:
        logger.info(f"请求 AI 字幕 URL: {url}")
        
        response = self.session.get(url, headers=self.headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data.get('code') != 0:
            logger.error(f"获取 AI 字幕 URL 失败: {data.get('message', '未知错误')}")
            raise Exception(f"获取 AI 字幕 URL 失败: {data.get('message', '未知错误')}")
        
        subtitle_url = data.get('data', {}).get('subtitle_url')
        if not subtitle_url:
            raise Exception("API 返回的 subtitle_url 为空")
        
        logger.info(f"成功获取 AI 字幕 URL")
        return subtitle_url
        
    except Exception as e:
        logger.error(f"获取 AI 字幕 URL 失败: {str(e)}")
        raise
```

### 改进 4：改进字幕获取函数

**新增函数**：`get_subtitle_with_ai_fallback(bvid: str, cid: str) -> dict`

```python
def get_subtitle_with_ai_fallback(self, bvid: str, cid: str) -> dict:
    """
    完整的字幕获取流程，包括 AI 字幕处理
    
    流程：
    1. 获取 aid
    2. 获取字幕信息
    3. 查找 AI 字幕
    4. 如果 AI 字幕 URL 为空，调用 /x/player/v2/ai/subtitle/search/stat 获取
    5. 获取字幕内容
    
    Args:
        bvid: 视频的 BV 号
        cid: 视频分P的 ID
        
    Returns:
        dict: 字幕数据，包括 metadata 和 subtitles
    """
    try:
        # 第一步：获取 aid
        aid = self.get_aid_from_bvid(bvid)
        
        # 第二步：获取字幕信息
        player_info = self.get_player_info(bvid, cid)
        
        if player_info.get('code') != 0:
            return {
                'success': False,
                'message': f"获取字幕信息失败: {player_info.get('message', '未知错误')}"
            }
        
        # 第三步：检查是否有字幕
        subtitle_data = player_info.get('data', {}).get('subtitle', {})
        subtitles = subtitle_data.get('subtitles', [])
        
        if not subtitles:
            return {
                'success': False,
                'message': '该视频没有可用字幕'
            }
        
        logger.info(f"找到 {len(subtitles)} 个字幕")
        
        # 第四步：查找 AI 字幕
        ai_subtitle = next((s for s in subtitles if s.get('lan') == 'ai-zh'), None)
        
        if not ai_subtitle:
            # 没有 AI 字幕，使用第一个字幕
            logger.info("没有找到 AI 字幕，使用第一个字幕")
            subtitle_url = subtitles[0].get('subtitle_url')
        else:
            logger.info("找到 AI 字幕")
            subtitle_url = ai_subtitle.get('subtitle_url')
            
            # 如果 AI 字幕 URL 为空，调用 API 获取
            if not subtitle_url:
                logger.info("AI 字幕 URL 为空，调用 API 获取")
                try:
                    subtitle_url = self.get_ai_subtitle_url(aid, cid)
                except Exception as e:
                    logger.error(f"获取 AI 字幕 URL 失败: {str(e)}")
                    # 降级到第一个字幕
                    logger.info("降级到第一个字幕")
                    subtitle_url = subtitles[0].get('subtitle_url')
        
        if not subtitle_url:
            return {
                'success': False,
                'message': '无法获取字幕 URL'
            }
        
        # 第五步：获取字幕内容
        subtitle_content = self.get_subtitle_content(subtitle_url)
        
        return {
            'success': True,
            'metadata': {
                'aid': aid,
                'bvid': bvid,
                'cid': cid,
                'subtitle_url': subtitle_url,
                'lan': ai_subtitle.get('lan') if ai_subtitle else subtitles[0].get('lan'),
                'lan_doc': ai_subtitle.get('lan_doc') if ai_subtitle else subtitles[0].get('lan_doc'),
            },
            'subtitles': subtitle_content.get('subtitles', []),
            'subtitle_text': subtitle_content.get('subtitle_text', '')
        }
        
    except Exception as e:
        logger.error(f"获取字幕失败: {str(e)}")
        return {
            'success': False,
            'message': f"获取字幕失败: {str(e)}"
        }
```

### 改进 5：新增 WBI 请求特殊处理函数

**新增函数**：`_handle_wbi_request(url: str, **kwargs) -> dict`

```python
def _handle_wbi_request(self, url: str, **kwargs) -> dict:
    """
    处理 WBI 请求的特殊逻辑
    
    对应 JS 版本的 fetchWbiRequest 函数
    
    Args:
        url: 请求 URL
        **kwargs: 其他请求参数
        
    Returns:
        dict: API 响应数据
    """
    try:
        logger.info(f"检测到 WBI 接口请求，进行特殊处理: {url}")
        
        # 确保 Cookie 被发送
        if 'headers' not in kwargs:
            kwargs['headers'] = self.headers.copy()
        
        # 发起请求
        response = self.session.get(url, timeout=10, **kwargs)
        response.raise_for_status()
        data = response.json()
        
        # 详细日志记录
        logger.info("===== WBI接口响应数据开始 =====")
        logger.info(f"状态码: {data.get('code')}")
        logger.info(f"消息: {data.get('message')}")
        logger.debug(f"完整数据: {json.dumps(data, ensure_ascii=False, indent=2)}")
        
        # 字幕数据特殊处理
        if data.get('code') == 0 and data.get('data', {}).get('subtitle'):
            subtitle_data = data['data']['subtitle']
            subtitles = subtitle_data.get('subtitles', [])
            
            logger.info("===== 字幕数据详情 =====")
            logger.info(f"字幕列表数量: {len(subtitles)}")
            
            for i, sub in enumerate(subtitles):
                logger.info(f"字幕[{i}]: id={sub.get('id')}, lan={sub.get('lan')}, "
                          f"lan_doc={sub.get('lan_doc')}, url={sub.get('subtitle_url')}")
            
            if not subtitles:
                logger.info("没有找到字幕数据")
            
            logger.info("===== 字幕数据详情结束 =====")
        
        # 错误重试机制
        if (data.get('code') == -400 and 
            data.get('message') and 
            'Key:' in data.get('message', '')):
            
            logger.warning(f"API返回参数错误，可能需要额外参数: {data.get('message')}")
            
            # 尝试添加 isGaiaAvoided=false 参数后再次请求
            if 'isGaiaAvoided=' not in url:
                separator = '&' if '?' in url else '?'
                retry_url = f"{url}{separator}isGaiaAvoided=false"
                
                logger.info(f"尝试添加参数后再次请求: {retry_url}")
                
                try:
                    retry_response = self.session.get(retry_url, timeout=10, **kwargs)
                    retry_response.raise_for_status()
                    retry_data = retry_response.json()
                    
                    logger.info("===== 参数补充后API响应 =====")
                    logger.info(f"状态码: {retry_data.get('code')}")
                    logger.info(f"消息: {retry_data.get('message')}")
                    logger.debug(f"完整数据: {json.dumps(retry_data, ensure_ascii=False, indent=2)}")
                    logger.info("===== 参数补充后API响应结束 =====")
                    
                    return retry_data
                    
                except Exception as retry_error:
                    logger.error(f"参数补充后请求仍然失败: {str(retry_error)}")
                    # 返回原始错误
        
        logger.info("===== WBI接口响应数据结束 =====")
        return data
        
    except Exception as e:
        logger.error(f"WBI请求处理出错: {str(e)}")
        raise
```

### 改进 6：改进统一请求函数

**修改 `_make_request` 方法**：

```python
def _make_request(self, url: str, **kwargs) -> dict:
    """
    统一的请求处理函数
    
    对应 JS 版本的 fetchWithHeaders 函数
    
    Args:
        url: 请求 URL
        **kwargs: 其他请求参数
        
    Returns:
        dict: API 响应数据
    """
    try:
        logger.info(f"发起API请求: {url}")
        
        # 检查是否是 WBI 接口
        is_wbi_request = '/x/player/wbi/v2' in url
        
        if is_wbi_request:
            logger.info("检测到WBI接口请求，进行特殊处理")
            return self._handle_wbi_request(url, **kwargs)
        
        # 普通请求处理
        if 'headers' not in kwargs:
            kwargs['headers'] = self.headers.copy()
        
        response = self.session.get(url, timeout=10, **kwargs)
        response.raise_for_status()
        data = response.json()
        
        logger.info(f"API请求响应: code={data.get('code')}, message={data.get('message')}")
        return data
        
    except Exception as e:
        logger.error(f"API请求出错: {str(e)}")
        raise
```

**修改 `_init_headers` 方法**：

```python
def _init_headers(self) -> dict:
    """初始化请求头"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Origin': 'https://www.bilibili.com',
        'Referer': 'https://www.bilibili.com/',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'Pragma': 'no-cache',
        'X-Wbi-UA': 'Win32.Chrome.109.0.0.0',  # 新增
    }
    
    # 添加 Cookie（如果存在）
    if self.cookie:
        headers['Cookie'] = self.cookie
    
    return headers
```

---

## 第三部分：实现步骤

### 步骤 1：添加新函数
- [ ] 添加 `get_aid_from_bvid()` 函数
- [ ] 添加 `get_ai_subtitle_url()` 函数
- [ ] 添加 `get_subtitle_with_ai_fallback()` 函数
- [ ] 添加 `_handle_wbi_request()` 函数

### 步骤 2：改进现有函数
- [ ] 改进 `get_player_info()` 函数
- [ ] 改进 `_make_request()` 方法（统一请求处理）
- [ ] 改进 `_init_headers()` 方法
- [ ] 改进 Cookie 管理

### 步骤 3：测试
- [ ] 单元测试：测试新函数
- [ ] 集成测试：测试完整流程
- [ ] 实际测试：使用真实视频测试

### 步骤 4：文档
- [ ] 更新代码注释
- [ ] 更新 README
- [ ] 更新 API 文档

---

## 第四部分：关键改进点总结

| 改进点 | 问题 | 解决方案 | 优先级 |
|--------|------|---------|--------|
| 添加 aid 获取 | 缺少 aid 参数 | 新增 `get_aid_from_bvid()` 函数 | 高 |
| AI 字幕 URL 处理 | URL 为空时无法处理 | 新增 `get_ai_subtitle_url()` 函数 | 高 |
| 完整流程函数 | 流程分散 | 新增 `get_subtitle_with_ai_fallback()` 函数 | 高 |
| WBI 请求特殊处理 | 缺少特殊处理逻辑 | 新增 `_handle_wbi_request()` 函数 | 高 |
| 统一请求函数 | 请求处理分散 | 改进 `_make_request()` 方法 | 高 |
| 请求头完善 | 缺少 X-Wbi-UA | 添加到 `_init_headers()` | 中 |
| Cookie 管理 | 管理不完善 | 改进 Cookie 处理逻辑 | 中 |

---

## 第五部分：预期效果

### 改进前
- ❌ AI 字幕获取不稳定
- ❌ 某些视频无法获取字幕
- ❌ 错误处理不完善

### 改进后
- ✅ AI 字幕获取稳定
- ✅ 支持所有类型的视频
- ✅ 完善的错误处理和降级方案
- ✅ 与 JS 版本保持一致

---

## 总结

通过添加 `aid` 获取步骤、改进 AI 字幕 URL 处理、完善请求头和 Cookie 管理，Python 版本将能够与 JS 版本保持一致，提高字幕获取的稳定性和成功率。

这些改进基于对 JS 版本完整流程的深入分析，确保了改进的正确性和有效性。
