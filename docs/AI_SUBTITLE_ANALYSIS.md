# B站AI字幕获取方案分析

## 任务1：视频下载功能验证

### 当前实现
✅ **是的，视频下载功能使用BBDown实现**

查看代码：`src/bilibili_extractor/modules/video_downloader.py`

```python
class VideoDownloader:
    def download(self, video_id: str, progress_callback: Optional[Callable] = None) -> Path:
        # 构建BBDown命令
        cmd = ["BBDown", video_url, "--work-dir", str(work_dir)]
```

### 结论
- ✅ 视频下载功能完全依赖BBDown
- ✅ BBDown是必需的外部依赖
- ✅ 保留BBDown是合理的，因为它是B站下载的最佳工具

---

## 任务2：SubBatch AI字幕获取原理分析

### 核心发现

SubBatch通过以下API获取AI字幕：

#### 1. 获取字幕信息API
```javascript
// 使用WBI签名的API（需要Cookie）
https://api.bilibili.com/x/player/wbi/v2?aid=${aid}&cid=${cid}

// 或者不需要WBI签名的API
https://api.bilibili.com/x/player/v2?cid=${cid}&bvid=${bvid}
```

#### 2. 获取AI字幕URL的API（关键！）
```javascript
// 这是BBDown无法获取的AI字幕API
https://api.bilibili.com/x/player/v2/ai/subtitle/search/stat?aid=${aid}&cid=${cid}

// 响应格式：
{
  "code": 0,
  "data": {
    "subtitle_url": "https://aisubtitle.hdslb.com/bfs/ai_subtitle/..."
  }
}
```

#### 3. 下载字幕内容
```javascript
// 使用返回的subtitle_url直接下载JSON格式字幕
fetch(subtitle_url)
```

### SubBatch的完整逻辑流程

```javascript
// 步骤1: 调用播放器API获取字幕信息
const subtitleInfoUrl = `https://api.bilibili.com/x/player/wbi/v2?aid=${aid}&cid=${cid}`;
const subtitleInfoData = await fetchWithHeaders(subtitleInfoUrl);

// 步骤2: 检查字幕列表
const subtitles = subtitleInfoData.data.subtitle.subtitles || [];

// 步骤3: 优先查找AI字幕（lan === 'ai-zh'）
const defaultSubtitle = subtitles.find((item) => item.lan === 'ai-zh');

// 步骤4: 检查字幕URL
const subtitleUrl = defaultSubtitle.subtitle_url;

if (!subtitleUrl) {
  // 情况A: 字幕URL为空 + 是AI字幕（lan以'ai-'开头）
  // 这种情况需要调用AI字幕专用API获取URL
  if (defaultSubtitle.lan && defaultSubtitle.lan.startsWith('ai-')) {
    const aiSubtitleUrl = `https://api.bilibili.com/x/player/v2/ai/subtitle/search/stat?aid=${aid}&cid=${cid}`;
    const aiSubtitleData = await fetchWithHeaders(aiSubtitleUrl);
    
    if (aiSubtitleData.code === 0 && aiSubtitleData.data.subtitle_url) {
      const fullAiSubtitleUrl = formatSubtitleUrl(aiSubtitleData.data.subtitle_url);
      // 下载并解析AI字幕
      const subtitleData = await fetch(fullAiSubtitleUrl).then(r => r.json());
      return formatAISubtitleData(subtitleData);
    }
  }
} else {
  // 情况B: 字幕URL存在（普通字幕或某些AI字幕）
  // 直接下载字幕内容
  const fullSubtitleUrl = formatSubtitleUrl(subtitleUrl);
  const subtitleData = await fetch(fullSubtitleUrl).then(r => r.json());
  
  // 检查是否是AI字幕格式，使用专用解析
  if (isAISubtitleFormat(subtitleData)) {
    return formatAISubtitleData(subtitleData);
  }
  
  // 普通字幕格式
  return formatRegularSubtitleData(subtitleData);
}
```

### 关键发现

1. **同一个API返回两种情况**：
   - 播放器API (`/x/player/wbi/v2`) 返回的字幕列表中
   - 普通字幕：`subtitle_url` 字段有值，可以直接下载
   - AI字幕：`subtitle_url` 字段为空，`lan` 以 `ai-` 开头

2. **AI字幕需要额外API**：
   - 当检测到 `lan.startsWith('ai-')` 且 `subtitle_url` 为空时
   - 需要调用专用API：`/x/player/v2/ai/subtitle/search/stat`
   - 这个API返回真正的字幕下载URL

3. **两种API的区别**：
   ```javascript
   // API 1: 获取字幕信息（包括普通字幕和AI字幕标识）
   https://api.bilibili.com/x/player/wbi/v2?aid=${aid}&cid=${cid}
   // 返回：subtitles[] 数组，包含 lan, subtitle_url 等字段
   
   // API 2: 获取AI字幕的实际URL（仅用于AI字幕）
   https://api.bilibili.com/x/player/v2/ai/subtitle/search/stat?aid=${aid}&cid=${cid}
   // 返回：data.subtitle_url - AI字幕的下载地址
   ```

### AI字幕格式特点

SubBatch检测AI字幕的方法：
```javascript
function isAISubtitleFormat(data) {
  // AI字幕有特殊的数据结构
  return data && data.body && Array.isArray(data.body);
}
```

---

## 任务3：实施方案

### 方案A：直接集成SubBatch的API调用逻辑（推荐）

#### 优点
- ✅ 不依赖浏览器环境
- ✅ 可以完全用Python实现
- ✅ 性能更好，更易维护
- ✅ 可以复用现有的BBDown Cookie机制

#### 实施步骤

1. **创建新模块：`ai_subtitle_fetcher.py`**
   - 实现B站API调用
   - 处理WBI签名（如果需要）
   - 解析AI字幕格式

2. **修改`subtitle_fetcher.py`**
   - 在BBDown失败后，尝试AI字幕API
   - 优先级：官方字幕 → AI字幕 → ASR

3. **API调用流程**
   ```python
   # 1. 获取视频信息（aid, cid）
   video_info = get_video_info(bvid)
   
   # 2. 检查是否有AI字幕
   player_info = get_player_info(aid, cid, cookie)
   
   # 3. 如果有AI字幕，调用AI字幕API
   if has_ai_subtitle(player_info):
       ai_subtitle_url = get_ai_subtitle_url(aid, cid, cookie)
       subtitle_data = download_subtitle(ai_subtitle_url)
       return parse_ai_subtitle(subtitle_data)
   ```

### 方案B：封装SubBatch插件（不推荐）

#### 缺点
- ❌ 需要浏览器环境（Selenium/Playwright）
- ❌ 性能开销大
- ❌ 部署复杂
- ❌ 维护困难

---

## 推荐实施方案：方案A + BBDown登录功能

### 完整流程设计

```
┌─────────────────────────────────────────────────────────┐
│ 1. Cookie管理                                            │
│    - 检查Cookie是否存在                                  │
│    - 如果不存在，调用BBDown登录                          │
│    - 保存Cookie供后续使用                                │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│ 2. 字幕获取（三级降级）                                  │
│    a. 尝试BBDown获取官方字幕                             │
│    b. 如果失败，尝试AI字幕API                            │
│    c. 如果还失败，使用ASR                                │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│ 3. 输出结果                                              │
└─────────────────────────────────────────────────────────┘
```

### 具体实施任务

#### Task 1: 实现BBDown登录功能
```python
# 新增：src/bilibili_extractor/modules/auth_manager.py

class AuthManager:
    def check_cookie(self) -> bool:
        """检查Cookie是否有效"""
        
    def login_with_qrcode(self) -> str:
        """使用BBDown的登录功能获取Cookie"""
        # 调用：BBDown login
        # 显示二维码
        # 等待扫码
        # 保存Cookie
        
    def get_cookie(self) -> str:
        """获取Cookie，如果不存在则提示登录"""
```

#### Task 2: 实现AI字幕获取
```python
# 新增：src/bilibili_extractor/modules/ai_subtitle_fetcher.py

class AISubtitleFetcher:
    def get_video_info(self, bvid: str) -> dict:
        """获取视频的aid和cid"""
        # API: https://api.bilibili.com/x/web-interface/view?bvid={bvid}
        
    def check_ai_subtitle(self, aid: str, cid: str, cookie: str) -> bool:
        """检查是否有AI字幕"""
        # API: https://api.bilibili.com/x/player/wbi/v2?aid={aid}&cid={cid}
        
    def get_ai_subtitle_url(self, aid: str, cid: str, cookie: str) -> str:
        """获取AI字幕URL"""
        # API: https://api.bilibili.com/x/player/v2/ai/subtitle/search/stat?aid={aid}&cid={cid}
        
    def download_ai_subtitle(self, subtitle_url: str) -> List[TextSegment]:
        """下载并解析AI字幕"""
```

#### Task 3: 修改主流程
```python
# 修改：src/bilibili_extractor/core/extractor.py

def extract(self, url: str) -> ExtractionResult:
    # 1. 检查Cookie
    if not self.auth_manager.check_cookie():
        print("需要登录以获取字幕")
        cookie = self.auth_manager.login_with_qrcode()
        self.config.cookie_file = cookie
    
    # 2. 尝试BBDown获取官方字幕
    try:
        return self.subtitle_fetcher.download_subtitles(video_id)
    except SubtitleNotFoundError:
        pass
    
    # 3. 尝试AI字幕
    try:
        return self.ai_subtitle_fetcher.fetch(video_id, self.config.cookie_file)
    except AISubtitleNotFoundError:
        pass
    
    # 4. 降级到ASR
    return self.asr_workflow(video_id)
```

---

## 关键API端点总结

### 1. 获取视频基本信息
```
GET https://api.bilibili.com/x/web-interface/view?bvid={bvid}
返回：aid, cid, title等
```

### 2. 获取播放器信息（包含字幕信息）
```
GET https://api.bilibili.com/x/player/wbi/v2?aid={aid}&cid={cid}
需要：Cookie（用于WBI签名）
返回：subtitle.subtitles[] - 字幕列表
      subtitle.subtitles[].ai_status - AI字幕标识（2=AI字幕）
```

### 3. 获取AI字幕URL（关键！）
```
GET https://api.bilibili.com/x/player/v2/ai/subtitle/search/stat?aid={aid}&cid={cid}
需要：Cookie
返回：data.subtitle_url - AI字幕文件URL
```

### 4. 下载字幕内容
```
GET {subtitle_url}
返回：JSON格式字幕数据
```

---

## BBDown登录功能

### BBDown支持的登录方式

```bash
# 1. 二维码登录（推荐）
BBDown login

# 2. TV端登录
BBDown login --tv

# 3. 使用access_key登录
BBDown login --access-key YOUR_ACCESS_KEY
```

### 登录后Cookie保存位置
- Windows: `%USERPROFILE%\.BBDown\BBDownCookies`
- Linux/Mac: `~/.BBDown/BBDownCookies`

### Python调用示例
```python
import subprocess
import os

def bbdown_login():
    """调用BBDown登录"""
    result = subprocess.run(
        ["BBDown", "login"],
        capture_output=True,
        text=True
    )
    
    # BBDown会显示二维码，用户扫码后自动保存Cookie
    if result.returncode == 0:
        # 读取保存的Cookie
        cookie_path = os.path.expanduser("~/.BBDown/BBDownCookies")
        with open(cookie_path, 'r') as f:
            return f.read()
    
    return None
```

---

## 实施优先级

### Phase 1: AI字幕支持（高优先级）
1. 实现`ai_subtitle_fetcher.py`模块
2. 集成到现有字幕获取流程
3. 测试AI字幕下载和解析

### Phase 2: Cookie管理（中优先级）
1. 实现`auth_manager.py`模块
2. 集成BBDown登录功能
3. 自动Cookie检查和刷新

### Phase 3: 用户体验优化（低优先级）
1. 改进登录提示
2. 添加Cookie有效期检查
3. 支持多账号管理

---

## 技术难点

### 1. WBI签名
某些API需要WBI签名，SubBatch已经实现了这个逻辑。我们可以：
- 方案A：参考SubBatch实现WBI签名
- 方案B：使用不需要WBI签名的API（`/x/player/v2`）

### 2. Cookie管理
- BBDown已经有完善的Cookie管理
- 我们只需要读取BBDown保存的Cookie文件

### 3. AI字幕格式解析
- SubBatch已经实现了AI字幕格式的解析
- 可以直接移植这部分逻辑到Python

---

## 总结

### 推荐方案
✅ **方案A：直接实现B站AI字幕API调用**

### 理由
1. 不需要浏览器环境
2. 性能更好
3. 更易维护
4. 可以复用BBDown的Cookie机制
5. SubBatch已经提供了完整的API调用示例

### 下一步
1. 创建`ai_subtitle_fetcher.py`模块
2. 实现B站API调用
3. 集成到现有流程
4. 添加BBDown登录支持
