# BBDown Cookie存储机制详解

## 源码分析

根据BBDown的C#源码（`BBDownLoginUtil.cs`），Cookie存储机制如下：

### Web登录（推荐）

```csharp
// 登录成功后保存Cookie
string cc = JsonDocument.Parse(w).RootElement.GetProperty("data").GetProperty("url").ToString();
await File.WriteAllTextAsync(
    Path.Combine(Program.APP_DIR, "BBDown.data"), 
    cc[(cc.IndexOf('?') + 1)..].Replace("&", ";").Replace(",", "%2C")
);
```

**关键信息**：
- 文件名：`BBDown.data`
- 位置：`Program.APP_DIR`（BBDown.exe所在目录）
- 格式：URL参数格式，`&`替换为`;`，`,`转义为`%2C`
- 示例：`SESSDATA=xxx;bili_jct=xxx;DedeUserID=xxx`

### TV登录

```csharp
// TV登录保存access_token
string cc = JsonDocument.Parse(web).RootElement.GetProperty("data").GetProperty("access_token").ToString();
await File.WriteAllTextAsync(
    Path.Combine(Program.APP_DIR, "BBDownTV.data"), 
    "access_token=" + cc
);
```

**关键信息**：
- 文件名：`BBDownTV.data`
- 位置：`Program.APP_DIR`（BBDown.exe所在目录）
- 格式：`access_token=xxx`

## Python实现要点

### 1. 查找BBDown.exe位置

```python
import shutil
from pathlib import Path

def get_bbdown_dir() -> Path:
    """获取BBDown.exe所在目录"""
    bbdown_path = shutil.which("BBDown")
    if not bbdown_path:
        raise FileNotFoundError("BBDown not found in PATH")
    return Path(bbdown_path).parent
```

### 2. 读取Cookie文件

```python
def read_bbdown_cookie(login_type: str = 'web') -> str:
    """读取BBDown保存的Cookie
    
    Args:
        login_type: 'web' or 'tv'
    
    Returns:
        Cookie字符串
    """
    bbdown_dir = get_bbdown_dir()
    
    if login_type == 'web':
        cookie_file = bbdown_dir / "BBDown.data"
    else:
        cookie_file = bbdown_dir / "BBDownTV.data"
    
    if not cookie_file.exists():
        raise FileNotFoundError(f"Cookie file not found: {cookie_file}")
    
    content = cookie_file.read_text(encoding='utf-8').strip()
    
    # Web登录需要将%2C转回逗号
    if login_type == 'web':
        content = content.replace('%2C', ',')
    
    return content
```

### 3. 验证Cookie格式

```python
def validate_cookie(content: str, login_type: str = 'web') -> bool:
    """验证Cookie格式是否正确
    
    Args:
        content: Cookie内容
        login_type: 'web' or 'tv'
    
    Returns:
        是否有效
    """
    if not content:
        return False
    
    if login_type == 'web':
        # Web登录必须包含SESSDATA
        return 'SESSDATA=' in content
    else:
        # TV登录必须包含access_token
        return 'access_token=' in content
```

### 4. 转换为HTTP请求头格式

```python
def cookie_to_header(content: str, login_type: str = 'web') -> str:
    """将Cookie转换为HTTP请求头格式
    
    Args:
        content: Cookie内容
        login_type: 'web' or 'tv'
    
    Returns:
        HTTP Cookie头的值
    """
    if login_type == 'web':
        # Web登录格式已经是正确的：SESSDATA=xxx;bili_jct=xxx
        return content
    else:
        # TV登录使用access_token（可能需要不同的处理）
        return content
```

## 使用示例

### 示例1：读取Web登录Cookie

```python
try:
    cookie = read_bbdown_cookie('web')
    print(f"Cookie: {cookie}")
    
    if validate_cookie(cookie, 'web'):
        print("Cookie is valid")
        
        # 用于HTTP请求
        headers = {
            'Cookie': cookie_to_header(cookie, 'web'),
            'User-Agent': 'Mozilla/5.0 ...'
        }
except FileNotFoundError as e:
    print(f"Error: {e}")
    print("Please run: BBDown login")
```

### 示例2：检查Cookie是否存在

```python
def check_cookie_exists(login_type: str = 'web') -> bool:
    """检查Cookie文件是否存在"""
    try:
        bbdown_dir = get_bbdown_dir()
        cookie_file = bbdown_dir / f"BBDown{'TV' if login_type == 'tv' else ''}.data"
        return cookie_file.exists()
    except FileNotFoundError:
        return False

if not check_cookie_exists():
    print("Cookie not found, please login first")
    print("Run: BBDown login")
```

### 示例3：调用BBDown登录

```python
import subprocess

def login_with_bbdown(login_type: str = 'web'):
    """调用BBDown登录功能
    
    Args:
        login_type: 'web' or 'tv'
    """
    print("Launching BBDown login...")
    print("Please scan QR code with Bilibili app")
    
    cmd = ["BBDown", "login"]
    if login_type == 'tv':
        cmd.append("--tv")
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        print("Login successful!")
        
        # 验证Cookie文件已创建
        if check_cookie_exists(login_type):
            cookie = read_bbdown_cookie(login_type)
            print(f"Cookie saved: {cookie[:50]}...")
        else:
            print("Warning: Cookie file not found after login")
    else:
        print(f"Login failed: {result.stderr}")
```

## 注意事项

### 1. Cookie格式转换

BBDown保存的Cookie格式：
```
SESSDATA=xxx;bili_jct=xxx;DedeUserID=xxx
```

这个格式可以直接用于HTTP请求头的Cookie字段，无需额外处理（除了%2C转义）。

### 2. 跨平台兼容性

BBDown.data的位置始终是BBDown.exe同目录，无论Windows、Linux还是Mac。只需要：
1. 确保BBDown在PATH中
2. 使用`shutil.which("BBDown")`找到可执行文件
3. 获取其父目录

### 3. Cookie有效期

- Cookie有效期通常为几个月
- 过期后需要重新登录
- 建议在API调用失败时检查Cookie是否过期

### 4. 安全性

- Cookie包含登录凭证，需要妥善保管
- 不要在日志中输出完整Cookie
- 建议设置文件权限（Unix系统）

## 测试用例

### 测试1：Cookie文件路径

```python
def test_get_bbdown_cookie_path():
    """测试获取Cookie文件路径"""
    bbdown_dir = get_bbdown_dir()
    cookie_file = bbdown_dir / "BBDown.data"
    
    assert cookie_file.name == "BBDown.data"
    assert cookie_file.parent == bbdown_dir
```

### 测试2：Cookie格式验证

```python
def test_validate_cookie_format():
    """测试Cookie格式验证"""
    # 有效的Web Cookie
    valid_web = "SESSDATA=abc123;bili_jct=def456;DedeUserID=789"
    assert validate_cookie(valid_web, 'web') == True
    
    # 无效的Web Cookie（缺少SESSDATA）
    invalid_web = "bili_jct=def456;DedeUserID=789"
    assert validate_cookie(invalid_web, 'web') == False
    
    # 有效的TV Cookie
    valid_tv = "access_token=xyz123"
    assert validate_cookie(valid_tv, 'tv') == True
    
    # 无效的TV Cookie
    invalid_tv = "token=xyz123"
    assert validate_cookie(invalid_tv, 'tv') == False
```

### 测试3：URL转义处理

```python
def test_cookie_url_decode():
    """测试Cookie中的URL转义"""
    # BBDown保存时将逗号转义为%2C
    encoded = "SESSDATA=abc%2C123;bili_jct=def456"
    decoded = encoded.replace('%2C', ',')
    
    assert decoded == "SESSDATA=abc,123;bili_jct=def456"
```

## 总结

BBDown的Cookie存储机制非常简单：
1. **位置固定**：BBDown.exe同目录
2. **文件名固定**：BBDown.data（Web）或BBDownTV.data（TV）
3. **格式简单**：URL参数格式，分号分隔
4. **易于读取**：纯文本文件，UTF-8编码

Python实现只需要：
1. 使用`shutil.which()`找到BBDown.exe
2. 读取同目录下的BBDown.data文件
3. 处理%2C转义
4. 验证SESSDATA字段存在
