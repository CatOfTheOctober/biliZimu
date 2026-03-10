# SubBatch 参考说明

## SubBatch 是什么？

SubBatch是一个Chrome浏览器扩展，用于批量下载B站视频字幕。它位于 `docs/reference/SubBatch/` 目录。

## 在本项目中的作用

### ❌ 不是直接引用
- SubBatch是JavaScript代码（浏览器扩展）
- 本项目是Python代码
- **无法直接调用或引用SubBatch的代码**

### ✅ 是技术参考
SubBatch作为技术调研和实现参考，我们从中学习了：

1. **WBI签名算法**
   - SubBatch实现了B站的WBI签名算法（JavaScript）
   - 我们用Python重新实现了相同的算法
   - 位置：`src/bilibili_extractor/modules/wbi_sign.py`

2. **API调用流程**
   - SubBatch展示了如何调用B站播放器API
   - 如何处理AI字幕（优先获取，URL为空时调用专用API）
   - 如何实现WBI API + v2 API的降级策略

3. **字幕获取逻辑**
   - 先尝试获取普通字幕
   - 检测AI字幕（subtitle_url为空）
   - 调用AI字幕专用API

## 代码对比

### SubBatch (JavaScript)
```javascript
// docs/reference/SubBatch/background.js
function getMixinKey(orig) {
  let temp = '';
  mixinKeyEncTab.forEach((n) => {
    temp += orig[n];
  });
  return temp.slice(0, 32);
}

function encWbi(params, img_key, sub_key) {
  const mixin_key = getMixinKey(img_key + sub_key);
  // ... 签名逻辑
}
```

### 本项目 (Python)
```python
# src/bilibili_extractor/modules/wbi_sign.py
def get_mixin_key(self, img_key: str, sub_key: str) -> str:
    """对img_key和sub_key进行字符顺序打乱编码。"""
    orig = img_key + sub_key
    return ''.join([orig[i] for i in self.MIXIN_KEY_ENC_TAB])[:32]

def enc_wbi(self, params: Dict[str, Any], img_key: str, sub_key: str) -> str:
    """为请求参数进行WBI签名。"""
    mixin_key = self.get_mixin_key(img_key, sub_key)
    # ... 签名逻辑（Python实现）
```

## 借鉴的内容

| 功能 | SubBatch | 本项目 | 说明 |
|------|----------|--------|------|
| WBI签名 | JavaScript实现 | Python重写 | 算法逻辑相同 |
| API调用 | 浏览器fetch | Python requests | 调用流程相同 |
| 字幕解析 | JSON解析 | Python解析 | 格式处理相同 |
| Cookie管理 | 浏览器Cookie | BBDown Cookie | 机制不同 |

## 为什么保留SubBatch代码？

1. **技术参考** - 作为实现的参考文档
2. **算法验证** - 验证WBI签名实现是否正确
3. **API文档** - 了解B站API的调用方式
4. **问题排查** - 遇到问题时可以对比实现

## 相关文档

- `docs/AI_SUBTITLE_ANALYSIS.md` - AI字幕技术分析
- `docs/SUBBATCH_LOGIC_ANALYSIS.md` - SubBatch逻辑完整分析
- `src/bilibili_extractor/modules/wbi_sign.py` - WBI签名Python实现
- `src/bilibili_extractor/modules/bilibili_api.py` - B站API客户端

## 许可证

SubBatch的许可证见 `docs/reference/SubBatch/LICENSE`

本项目的WBI签名实现是基于公开的技术文档和SubBatch的参考实现，使用Python重新编写。
