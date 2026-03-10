# WBI 签名实现指南

## 核心理解

### WBI 签名的本质

WBI 签名是 B 站为了防止 API 滥用而设计的一种请求验证机制。它通过以下方式工作：

1. **获取动态密钥**：从 `/x/web-interface/nav` 获取 `img_key` 和 `sub_key`
2. **生成混合密钥**：通过特定算法混合两个密钥
3. **签名请求参数**：使用混合密钥对请求参数进行 MD5 签名
4. **验证请求**：B 站服务器验证签名的有效性

### 关键点

- ✅ **只有特定接口需要 WBI 签名**（如 `/x/space/wbi/arc/search`）
- ❌ **不是所有包含 `wbi` 的接口都需要签名**（如 `/x/player/wbi/v2`）
- ⏰ **签名包含时间戳**，每次请求都会变化
- 🔐 **签名是为了防止滥用**，不是为了隐藏数据

## Python 实现对比

### ❌ 错误的实现（Python 原版）

```python
def get_player_info(self, aid: int, cid: int) -> Dict[str, Any]:
    """错误：对不需要签名的接口进行了签名"""
    
    # 获取 WBI 密钥
    wbi_keys = get_wbi_keys()
    img_key, sub_key = wbi_keys
    
    # 错误：对 /x/player/wbi/v2 进行 WBI 签名
    params = {'aid': aid, 'cid': cid}
    signed_params = encode_wbi(params, img_key, sub_key)
    
    # 构建 URL（包含签名）
    query_string = '&'.join(f"{k}={v}" for k, v in signed_params.items())
    url = f"https://api.bilibili.com/x/player/wbi/v2?{query_string}"
    
    # 发起请求
    response = self.session.get(url)
    # 结果：API 返回空字幕列表
```

**问题**：
- `/x/player/wbi/v2` 不需要 WBI 签名
- 添加不必要的签名导致 API 返回错误结果
- 浪费计算资源

### ✅ 正确的实现（修复后）

```python
def get_player_info(self, aid: int, cid: int) -> Dict[str, Any]:
    """正确：直接使用原始 URL，不进行签名"""
    
    # 直接构建 URL，不进行签名
    url = f"https://api.bilibili.com/x/player/wbi/v2?aid={aid}&cid={cid}"
    
    # 发起请求
    response = self.session.get(url)
    # 结果：API 返回正确的字幕列表
```

**优点**：
- 简洁明了
- 不浪费计算资源
- 与 JS 版本一致

## 何时使用 WBI 签名

### 需要 WBI 签名的接口

```python
# 例子：获取用户视频列表
def get_user_videos(self, mid: int, page: int = 1) -> Dict[str, Any]:
    """获取用户视频列表（需要 WBI 签名）"""
    
    # 获取 WBI 密钥
    wbi_keys = get_wbi_keys()
    img_key, sub_key = wbi_keys
    
    # 准备参数
    params = {
        'mid': mid,
        'pn': page,
        'ps': 30,
        'tid': 0,
        'keyword': '',
        'order': 'pubdate',
        'web_location': 1550101,
        'order_avoided': True,
    }
    
    # 计算签名
    signed_params = encode_wbi(params, img_key, sub_key)
    
    # 构建 URL
    query_string = urllib.parse.urlencode(signed_params)
    url = f"https://api.bilibili.com/x/space/wbi/arc/search?{query_string}"
    
    # 发起请求
    response = self.session.get(url)
    return response.json()
```

### 不需要 WBI 签名的接口

```python
# 例子 1：获取视频信息
def get_video_info(self, bvid: str) -> Dict[str, Any]:
    """获取视频信息（不需要 WBI 签名）"""
    url = f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}"
    response = self.session.get(url)
    return response.json()

# 例子 2：获取播放器信息
def get_player_info(self, aid: int, cid: int) -> Dict[str, Any]:
    """获取播放器信息（不需要 WBI 签名）"""
    url = f"https://api.bilibili.com/x/player/wbi/v2?aid={aid}&cid={cid}"
    response = self.session.get(url)
    return response.json()

# 例子 3：获取 AI 字幕 URL
def get_ai_subtitle_url(self, aid: int, cid: int) -> Optional[str]:
    """获取 AI 字幕 URL（不需要 WBI 签名）"""
    url = f"https://api.bilibili.com/x/player/v2/ai/subtitle/search/stat?aid={aid}&cid={cid}"
    response = self.session.get(url)
    data = response.json()
    return data.get('data', {}).get('subtitle_url')
```

## WBI 签名算法详解

### 步骤 1: 获取 WBI 密钥

```python
def get_wbi_keys() -> Optional[Tuple[str, str]]:
    """获取最新的 img_key 和 sub_key"""
    try:
        response = requests.get('https://api.bilibili.com/x/web-interface/nav')
        data = response.json()
        
        img_url = data['data']['wbi_img']['img_url']
        sub_url = data['data']['wbi_img']['sub_url']
        
        # 提取文件名（去掉路径和扩展名）
        img_key = img_url.rsplit('/', 1)[1].split('.')[0]
        sub_key = sub_url.rsplit('/', 1)[1].split('.')[0]
        
        return img_key, sub_key
    except Exception as e:
        logger.error(f"Failed to get WBI keys: {e}")
        return None
```

### 步骤 2: 生成混合密钥

```python
MIXIN_KEY_ENC_TAB = [
    46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35, 27, 43, 5, 49,
    33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13, 37, 48, 7, 16, 24, 55, 40,
    61, 26, 17, 0, 1, 60, 51, 30, 4, 22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11,
    36, 20, 34, 44, 52
]

def get_mixin_key(orig: str) -> str:
    """对 img_key + sub_key 进行字符顺序打乱编码"""
    if len(orig) < 64:
        raise ValueError(f"Input length must be at least 64, got {len(orig)}")
    
    # 使用映射表重排字符
    temp = ''.join(orig[i] for i in MIXIN_KEY_ENC_TAB)
    
    # 取前 32 个字符
    return temp[:32]
```

### 步骤 3: 计算签名

```python
def encode_wbi(params: Dict[str, Any], img_key: str, sub_key: str) -> Dict[str, Any]:
    """为请求参数进行 WBI 签名"""
    
    # 生成 mixin_key
    mixin_key = get_mixin_key(img_key + sub_key)
    
    # 添加时间戳
    curr_time = round(time.time())
    params['wts'] = curr_time
    
    # 按 key 排序参数
    params = dict(sorted(params.items()))
    
    # 过滤特殊字符 !'()*
    params = {
        k: ''.join(filter(lambda chr: chr not in "!'()*", str(v)))
        for k, v in params.items()
    }
    
    # 序列化参数
    query = urllib.parse.urlencode(params)
    
    # 计算 MD5 签名
    wbi_sign = hashlib.md5((query + mixin_key).encode()).hexdigest()
    
    # 添加签名到参数
    params['w_rid'] = wbi_sign
    
    return params
```

## 调试技巧

### 1. 打印中间结果

```python
def encode_wbi_debug(params: Dict[str, Any], img_key: str, sub_key: str) -> Dict[str, Any]:
    """带调试输出的 WBI 签名"""
    
    print(f"原始参数: {params}")
    
    mixin_key = get_mixin_key(img_key + sub_key)
    print(f"Mixin Key: {mixin_key}")
    
    curr_time = round(time.time())
    params['wts'] = curr_time
    print(f"添加时间戳: {params}")
    
    params = dict(sorted(params.items()))
    print(f"排序后: {params}")
    
    params = {
        k: ''.join(filter(lambda chr: chr not in "!'()*", str(v)))
        for k, v in params.items()
    }
    print(f"过滤后: {params}")
    
    query = urllib.parse.urlencode(params)
    print(f"查询字符串: {query}")
    
    wbi_sign = hashlib.md5((query + mixin_key).encode()).hexdigest()
    print(f"签名: {wbi_sign}")
    
    params['w_rid'] = wbi_sign
    return params
```

### 2. 对比 JS 和 Python 的签名

```python
# 使用相同的参数和密钥
params = {'mid': 123, 'pn': 1, 'ps': 30}
img_key = "7cd084941338484aae1ad9425b84077c"
sub_key = "4932caff0ff746eab6f01bf08b70ac45"

# Python 版本
py_result = encode_wbi(params.copy(), img_key, sub_key)
print(f"Python: {py_result}")

# 与 JS 版本对比
# 应该得到相同的 w_rid 值
```

## 常见错误

### 错误 1: 对所有 wbi 接口都进行签名

```python
# ❌ 错误
url = f"https://api.bilibili.com/x/player/wbi/v2?aid={aid}&cid={cid}"
signed_params = encode_wbi({'aid': aid, 'cid': cid}, img_key, sub_key)
# 结果：API 返回错误

# ✅ 正确
url = f"https://api.bilibili.com/x/player/wbi/v2?aid={aid}&cid={cid}"
# 不进行签名
```

### 错误 2: 签名后不添加到 URL

```python
# ❌ 错误
signed_params = encode_wbi(params, img_key, sub_key)
url = f"https://api.bilibili.com/x/space/wbi/arc/search?mid={mid}&pn={pn}"
# 结果：API 返回 401 Unauthorized

# ✅ 正确
signed_params = encode_wbi(params, img_key, sub_key)
query_string = urllib.parse.urlencode(signed_params)
url = f"https://api.bilibili.com/x/space/wbi/arc/search?{query_string}"
```

### 错误 3: 参数顺序不对

```python
# ❌ 错误
params = {'ps': 30, 'pn': 1, 'mid': 123}  # 未排序
signed_params = encode_wbi(params, img_key, sub_key)

# ✅ 正确
params = {'mid': 123, 'pn': 1, 'ps': 30}  # 已排序
signed_params = encode_wbi(params, img_key, sub_key)
```

## 总结

### 关键要点

1. **WBI 签名只用于特定接口**（如 `/x/space/wbi/arc/search`）
2. **不是所有包含 `wbi` 的接口都需要签名**（如 `/x/player/wbi/v2`）
3. **签名包含时间戳**，每次请求都会变化
4. **签名是为了防止 API 滥用**，不是为了隐藏数据

### Python 实现清单

- ✅ `get_wbi_keys()` - 获取 WBI 密钥
- ✅ `get_mixin_key()` - 生成混合密钥
- ✅ `encode_wbi()` - 计算签名
- ✅ 知道何时使用签名
- ✅ 知道何时不使用签名

### 参考资源

- WBI 签名文档：https://xtcqinghe.github.io/bac/docs/misc/sign/wbi.html
- B 站 API 参考：https://github.com/SocialSisterYi/bilibili-API-collect
- SubBatch 源代码：`docs/reference/SubBatch/background.js`
