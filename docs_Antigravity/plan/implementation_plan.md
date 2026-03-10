# 修复实施方案：跳过 TextExtractor 中的字幕检查逻辑

## 1. 问题分析
用户在运行 `下载字幕.py` 中新加的代码时，触发了 `TextExtractor.extract(url)`。此方法内部目前的工作流是：
1. 验证URL -> 2. 检查Cookie -> **3. 尝试调用 `subtitle_fetcher.fetch_subtitle()` 获取字幕** -> 4. 如果失败则走 ASR 流程。
因为 `下载字幕.py` 在外部调用 `extract` 前**已经经历了获取字幕失败的分支**，所以 `extract()` 内部第 3 步纯属多余，且极可能因为 API 问题报错（例如 `412 Precondition Failed`），这不仅拖慢速度，还中断了我们所需的降级视频下载 + ASR。

## 2. 实施方案
为了解决这个问题，我们需要让 `TextExtractor` 支持一个“直接跳过字幕抓取”的标志，以便在 `下载字幕.py` 遇到空字幕时直接通过标志进入第 4 步(ASR)。

### [MODIFY] `src/bilibili_extractor/core/extractor.py` (file:///d:/Kiro_proj/Test1/src/bilibili_extractor/core/extractor.py)
在 `extract` 方法签名中增加 `force_asr: bool = False` 形参：
```python
def extract(self, url: str, progress_callback: Optional[Callable] = None, force_asr: bool = False) -> ExtractionResult:
```
修改第 2 步逻辑（大概第 113 行）：
```python
            # 2. 尝试获取字幕（优先Bilibili API） - 如果没有强制要求 ASR
            segments = None
            if not force_asr:
                self.logger.info("Step 2: Checking for subtitles")
                try:
                    segments = self.subtitle_fetcher.fetch_subtitle(video_id, url)
                except Exception as e:
                    self.logger.warning(f"Failed to fetch subtitle from API: {e}, will fallback to ASR.")
```

### [MODIFY] `下载字幕.py` (file:///d:/Kiro_proj/Test1/%E4%B8%8B%E8%BD%BD%E5%AD%97%E5%B9%95.py)
在调用 `extractor.extract(url)` 时传递 `force_asr=True`：
同时，原逻辑中共有两处调用的地方（字幕为空、字幕获取失败），两处都要更新。
```python
asr_result = extractor.extract(url, force_asr=True)
```

## 3. 验证计划
无需手动验证，按照计划执行完替换即可。

请问该修正方案是否符合预期？
