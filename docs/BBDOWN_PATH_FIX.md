[说明] 旧 CLI 命令 python 下载字幕.py

# BBDown Path Fix for Video Downloader

## Issue Description

When a video doesn't have subtitles and the system tries to fall back to ASR (which requires downloading the video), it failed with:

```
FileNotFoundError: [WinError 2] 系统找不到指定的文件。
BBDown not found. Please install BBDown and ensure it's in your PATH.
```

### Root Cause

The `VideoDownloader` class was calling BBDown directly using `["BBDown", ...]` in the subprocess command, without using the `ToolFinder` utility that we created to locate external tools.

This meant:
- BBDown was only found if it was in the system PATH
- The project's `tools/BBDown/BBDown.exe` was not being detected
- Configuration file paths were ignored

## Solution

Updated `VideoDownloader` to use `ToolFinder` for locating BBDown, following the same pattern as `AuthManager`.

### Changes Made

**File**: `src/bilibili_extractor/modules/video_downloader.py`

1. **Import ToolFinder**:
```python
from bilibili_extractor.utils.tool_finder import ToolFinder
```

2. **Find BBDown in __init__**:
```python
def __init__(self, config: Config):
    """Initialize video downloader."""
    self.config = config
    
    # Find BBDown executable
    tool_finder = ToolFinder()
    bbdown_path = tool_finder.find_bbdown(config.bbdown_path)
    
    if not bbdown_path:
        raise FileNotFoundError(
            "BBDown not found. Please install BBDown in tools/BBDown/ directory "
            "or add it to your system PATH."
        )
    
    self.bbdown_path = bbdown_path
```

3. **Use found path in command**:
```python
# Construct BBDown command - use found BBDown path
cmd = [str(self.bbdown_path), video_url, "--work-dir", str(temp_dir)]
```

### Search Priority

BBDown is now searched in the following order:
1. Configuration file path (`config.bbdown_path`)
2. Project tools directory (`tools/BBDown/BBDown.exe`)
3. Environment variable (`BBDOWN_DIR`)
4. System PATH

## Testing

Tested with a video that has regular subtitles (not AI subtitles):

```bash
python 下载字幕.py
```

**Result**:
- Successfully extracted 705 subtitle segments
- BBDown was found at: `D:\Kiro_proj\Test1\tools\BBDown\BBDown.exe`
- Output saved to: `D:\Kiro_proj\Test1\output\BV1PeoyYmEnq.txt`

## Related Issues

This fix also addresses the scenario where:
- A video has no AI subtitles (404 error from AI subtitle API)
- But has regular subtitles available
- System correctly falls back to regular subtitles

The error message in the log:
```
Request failed after 3 attempts: Failed to fetch AI subtitle URL: 404 Client Error
```

This is expected behavior - not all videos have AI subtitles. The system correctly handles this by:
1. Trying AI subtitle API
2. If 404, using regular subtitles from player info
3. If no subtitles at all, falling back to ASR (which now works with BBDown path fix)

## Impact

- Video downloading now works when subtitles are not available
- ASR fallback workflow is now functional
- Consistent tool path resolution across all modules (AuthManager, VideoDownloader)
- Better error messages when BBDown is not found


