# Implementation Plan: B站AI字幕支持和Cookie管理

## Overview

本实施计划将为B站视频文字提取系统添加AI字幕支持和自动Cookie管理功能。实现策略：(1) 创建AuthManager管理Cookie和BBDown登录，(2) 创建BilibiliAPI封装B站API调用，(3) 创建SubtitleParser解析不同格式字幕，(4) 增强SubtitleFetcher实现优先级降级机制，(5) 更新CLI集成新功能。

## Tasks

- [x] 1. 创建Cookie管理模块（AuthManager）
  - [x] 1.1 实现AuthManager基础类和Cookie检测
    - 创建`src/bilibili_extractor/modules/auth_manager.py`
    - 实现`__init__`方法接收Config参数
    - 实现`get_bbdown_cookie_path()`方法查找BBDown.data位置
    - 实现`check_cookie()`方法检查Cookie文件是否存在
    - 实现`get_cookie_path()`方法返回Cookie文件路径
    - _Requirements: 1.1, 1.2_

  - [x] 1.2 实现Cookie读取和验证
    - 实现`read_cookie_content(cookie_path)`方法读取Cookie文件
    - 处理%2C转义（替换为逗号）
    - 实现`validate_cookie_format(cookie_path)`方法验证Cookie格式
    - 检查SESSDATA字段是否存在
    - 支持Web登录（BBDown.data）和TV登录（BBDownTV.data）
    - _Requirements: 1.2, 1.5_

  - [x] 1.3 实现BBDown登录集成
    - 实现`login_with_bbdown()`方法调用BBDown登录
    - 使用subprocess运行`BBDown login`命令
    - 显示用户提示信息（扫描二维码）
    - 验证登录后Cookie文件已创建
    - 处理登录失败情况并抛出AuthenticationError
    - _Requirements: 1.3, 1.4_

  - [ ]* 1.4 编写AuthManager单元测试
    - **Property 1: Cookie Format Validity**
    - **Property 2: Cookie Location Detection**
    - **Property 3: Login Trigger on Invalid Cookie**
    - **Validates: Requirements 1.1, 1.2, 1.3, 1.5**

- [x] 2. 创建B站API客户端模块（BilibiliAPI）
  - [x] 2.1 实现BilibiliAPI基础类和HTTP会话
    - 创建`src/bilibili_extractor/modules/bilibili_api.py`
    - 实现`__init__`方法接收Cookie参数
    - 初始化requests.Session并配置headers（User-Agent, Referer）
    - 实现连接池和超时设置（连接5秒，读取30秒）
    - 添加简单的内存缓存字典
    - _Requirements: 2.1, 10.2_


  - [x] 2.2 实现视频信息API调用
    - 实现`get_video_info(bvid)`方法
    - 调用`https://api.bilibili.com/x/web-interface/view?bvid={bvid}`
    - 解析响应获取aid、cid、title等信息
    - 实现缓存机制避免重复请求
    - 处理API错误响应（code != 0）
    - _Requirements: 2.1, 10.1_

  - [x] 2.3 实现播放器信息API调用
    - 实现`get_player_info(aid, cid)`方法
    - 调用`https://api.bilibili.com/x/player/wbi/v2?aid={aid}&cid={cid}`
    - 添加Cookie到请求头
    - 解析响应获取字幕列表（subtitle.subtitles）
    - 处理需要登录的情况（code=-101）
    - _Requirements: 2.2, 2.5_

  - [x] 2.4 实现AI字幕URL获取API
    - 实现`get_ai_subtitle_url(aid, cid)`方法
    - 调用`https://api.bilibili.com/x/player/v2/ai/subtitle/search/stat?aid={aid}&cid={cid}`
    - 添加Cookie到请求头
    - 从响应中提取subtitle_url字段
    - 处理AI字幕不可用的情况
    - _Requirements: 2.3, 3.2_

  - [x] 2.5 实现字幕下载和URL格式化
    - 实现`download_subtitle(subtitle_url)`方法下载字幕JSON
    - 实现`format_subtitle_url(url)`方法处理相对路径
    - 如果URL以//开头，添加https:前缀
    - 如果URL以/开头，添加https://api.bilibili.com前缀
    - 返回字幕JSON数据
    - _Requirements: 2.4, 2.6_

  - [x] 2.6 实现API重试和错误处理
    - 添加重试装饰器（最多3次，指数退避）
    - 处理网络超时异常
    - 处理429限流响应（等待后重试）
    - 抛出BilibiliAPIError包含详细错误信息
    - 记录所有API调用和错误日志
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_

  - [ ]* 2.7 编写BilibiliAPI单元测试
    - **Property 4: API Video Info Retrieval**
    - **Property 5: AI Subtitle URL Resolution**
    - **Property 6: Relative URL Conversion**
    - **Property 17: API Retry Behavior**
    - **Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 8.1, 8.2**

- [x] 3. 创建字幕解析模块（SubtitleParser）
  - [x] 3.1 实现字幕格式检测和解析
    - 创建`src/bilibili_extractor/modules/subtitle_parser.py`
    - 实现`is_ai_subtitle_format(data)`静态方法检测AI字幕格式
    - 实现`parse_subtitle(data)`静态方法统一解析入口
    - 实现`parse_ai_subtitle(data)`静态方法解析AI字幕
    - 实现`parse_regular_subtitle(data)`静态方法解析普通字幕
    - 从body数组提取from、to、content字段
    - _Requirements: 4.1, 4.2, 4.3_

  - [x] 3.2 实现时间戳转换和验证
    - 转换时间戳为float类型（秒）
    - 验证start_time < end_time
    - 按start_time升序排序TextSegment列表
    - 验证相邻片段无重叠（前end_time ≤ 后start_time）
    - 设置source字段为'subtitle'
    - _Requirements: 4.4, 4.5, 4.6, 6.1, 6.2, 6.3_

  - [ ]* 3.3 编写SubtitleParser单元测试
    - **Property 9: Subtitle Format Detection**
    - **Property 10: Complete Field Extraction**
    - **Property 11: Timestamp Validity and Ordering**
    - **Property 15: Timestamp Type Conversion**
    - **Validates: Requirements 4.1, 4.2, 4.3, 4.5, 4.6, 6.1, 6.2, 6.3**

- [x] 4. 增强SubtitleFetcher实现优先级机制
  - [x] 4.1 添加BilibiliAPI集成到SubtitleFetcher
    - 修改`src/bilibili_extractor/modules/subtitle_fetcher.py`
    - 在`__init__`中初始化BilibiliAPI实例
    - 添加`fetch_from_bilibili_api(bvid, cookie)`方法
    - 实现完整的SubBatch逻辑（视频信息→播放器信息→字幕下载→解析）
    - 优先查找'ai-zh'字幕
    - 处理AI字幕URL为空的情况（调用AI字幕API）
    - _Requirements: 3.1, 3.2, 5.1_

  - [x] 4.2 实现字幕获取优先级降级
    - 修改`fetch_subtitle`方法实现优先级逻辑
    - 首先尝试`fetch_from_bilibili_api`
    - 如果抛出SubtitleNotFoundError，记录日志并返回None
    - 保留现有的BBDown字幕获取作为备用（可选）
    - 确保返回的TextSegment包含正确的source字段
    - _Requirements: 3.4, 5.2, 5.3_

  - [ ]* 4.3 编写SubtitleFetcher集成测试
    - **Property 7: AI Subtitle Priority**
    - **Property 8: Subtitle Fallback Logic**
    - **Property 12: Subtitle Fetching Priority**
    - **Validates: Requirements 3.1, 3.4, 5.1, 5.2**

- [x] 5. 更新TextExtractor集成Cookie管理
  - [x] 5.1 集成AuthManager到TextExtractor
    - 修改`src/bilibili_extractor/core/extractor.py`
    - 在`__init__`中初始化AuthManager实例
    - 在`extract`方法开始时调用`auth_manager.check_cookie()`
    - 如果Cookie无效，调用`auth_manager.login_with_bbdown()`
    - 获取Cookie内容并传递给SubtitleFetcher
    - _Requirements: 1.1, 1.3, 9.1_

  - [x] 5.2 实现字幕到ASR的降级流程
    - 修改`extract`方法的字幕获取逻辑
    - 首先调用`subtitle_fetcher.fetch_subtitle`获取字幕
    - 如果返回None或空列表，记录日志并降级到ASR
    - 确保ASR生成的TextSegment的source为'asr'
    - 确保最终返回非空的TextSegment列表
    - _Requirements: 5.2, 5.4, 5.5_

  - [ ]* 5.3 编写TextExtractor集成测试
    - **Property 13: Source Field Accuracy**
    - **Property 14: Non-Empty Result Guarantee**
    - **Validates: Requirements 5.3, 5.4, 5.5**

- [x] 6. 更新Config支持Cookie配置
  - [x] 6.1 添加Cookie相关配置项
    - 修改`src/bilibili_extractor/core/config.py`
    - 在Config类添加`cookie_file: Optional[str]`字段
    - 在Config类添加`auto_login: bool = True`字段
    - 在Config类添加`login_type: str = 'web'`字段（'web'或'tv'）
    - 更新ConfigLoader支持从配置文件读取这些字段
    - _Requirements: 9.4_

- [x] 7. 更新CLI支持新功能
  - [x] 7.1 添加Cookie相关命令行参数
    - 修改`src/bilibili_extractor/cli.py`
    - 添加`--cookie`参数指定Cookie文件路径
    - 添加`--login`参数强制触发登录
    - 添加`--check-cookie`参数检查Cookie状态
    - 添加`--no-auto-login`参数禁用自动登录
    - _Requirements: 9.2, 9.3, 9.4_

  - [x] 7.2 实现Cookie状态检查命令
    - 实现`--check-cookie`功能
    - 显示Cookie文件路径
    - 显示Cookie是否有效
    - 显示SESSDATA前缀（不显示完整内容）
    - 显示Cookie过期时间（如果可解析）
    - _Requirements: 9.3, 12.4_

  - [x] 7.3 更新输出显示字幕来源
    - 修改`display_summary`函数
    - 显示文本来源（Bilibili API / ASR）
    - 如果是字幕，显示字幕类型（AI / Regular）
    - 更新输出格式包含source信息
    - _Requirements: 9.5_

- [ ] 8. 添加数据模型
  - [ ] 8.1 创建字幕相关数据模型
    - 修改`src/bilibili_extractor/core/models.py`
    - 添加`SubtitleInfo`数据类（lan, lan_doc, subtitle_url, ai_status）
    - 添加`is_ai_subtitle()`方法
    - 添加`needs_ai_api()`方法
    - 添加`PlayerResponse`数据类（code, message, data）
    - 添加`get_subtitles()`方法
    - 添加`find_ai_subtitle()`方法
    - 添加`AISubtitleResponse`数据类（code, message, data）
    - 添加`get_subtitle_url()`方法
    - _Requirements: 2.2, 2.3, 3.1_

  - [ ] 8.2 创建Cookie数据模型
    - 添加`CookieInfo`数据类（path, content, is_valid, login_type）
    - 实现`from_bbdown(login_type)`类方法
    - 实现`_validate_content(content, login_type)`静态方法
    - 实现`to_header_string()`方法转换为HTTP请求头格式
    - _Requirements: 1.2, 1.5_

- [x] 9. 添加异常类
  - [x] 9.1 创建认证相关异常
    - 修改或创建`src/bilibili_extractor/core/exceptions.py`
    - 添加`AuthenticationError`异常类
    - 添加`CookieNotFoundError`异常类
    - 添加`CookieInvalidError`异常类
    - _Requirements: 1.3, 8.4_

  - [x] 9.2 创建API相关异常
    - 添加`BilibiliAPIError`异常类
    - 添加`VideoNotFoundError`异常类
    - 添加`SubtitleNotFoundError`异常类（如果不存在）
    - 确保所有异常包含详细错误信息
    - _Requirements: 2.5, 8.4, 11.4_

- [x] 10. 实现安全和验证功能
  - [x] 10.1 实现输入验证
    - 创建`src/bilibili_extractor/utils/validators.py`
    - 实现`validate_bvid(bvid)`函数验证BVID格式
    - 实现`validate_file_path(path, allowed_dir)`函数验证路径安全
    - 实现`validate_api_response(response, expected_fields)`函数验证API响应
    - 实现输入转义函数防止注入
    - _Requirements: 11.1, 11.2, 11.3, 11.5_

  - [x] 10.2 实现Cookie安全存储
    - 在AuthManager中实现`save_cookie_securely(cookie_path, content)`方法
    - 在Unix系统设置文件权限为600
    - 在Windows系统使用适当的权限设置
    - 记录安全日志但不输出Cookie内容
    - _Requirements: 7.1, 7.2, 7.3, 7.4_

  - [ ]* 10.3 编写安全功能测试
    - **Property 16: Log Content Sanitization**
    - **Property 20: Custom Cookie File Usage**
    - **Property 25: BVID Format Validation**
    - **Property 26: Path Safety Validation**
    - **Property 27: API Response Structure Validation**
    - **Property 28: Input Sanitization**
    - **Validates: Requirements 7.2, 11.1, 11.2, 11.3, 11.5, 12.4**

- [x] 11. 实现性能优化
  - [x] 11.1 实现API请求缓存
    - 在BilibiliAPI中实现LRU缓存
    - 缓存视频信息API响应（基于bvid）
    - 缓存播放器信息API响应（基于aid+cid）
    - 设置合理的缓存大小限制（如100条）
    - 实现缓存过期机制（TTL）
    - _Requirements: 10.1, 10.5_

  - [x] 11.2 实现请求速率限制
    - 创建`rate_limit`装饰器
    - 限制每秒最多2个API请求
    - 使用时间戳跟踪请求间隔
    - 自动延迟过快的请求
    - _Requirements: 10.4_

  - [ ]* 11.3 编写性能优化测试
    - **Property 22: API Response Caching**
    - **Property 23: Rate Limiting Enforcement**
    - **Property 24: LRU Cache Eviction**
    - **Validates: Requirements 10.1, 10.4, 10.5**

- [ ] 12. 实现日志记录
  - [x] 12.1 添加详细的操作日志
    - 在所有关键操作添加日志记录
    - 记录字幕获取开始和结果（视频ID、获取方式）
    - 记录API调用详情（URL、参数、响应码）
    - 记录降级到ASR的原因
    - 记录Cookie操作（不记录Cookie内容）
    - 所有日志包含时间戳
    - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5_

  - [ ]* 12.2 编写日志记录测试
    - **Property 29: Operation Logging Completeness**
    - **Validates: Requirements 12.1, 12.2, 12.3, 12.5**

- [x] 13. Checkpoint - 核心功能验证
  - 手动测试AuthManager的Cookie检测和登录功能
  - 手动测试BilibiliAPI的各个API调用
  - 手动测试SubtitleParser解析不同格式字幕
  - 验证所有单元测试通过
  - 确认没有语法错误和类型错误
  - 询问用户是否有问题或需要调整

- [ ] 14. 集成测试和端到端验证
  - [ ] 14.1 编写端到端集成测试
    - 创建`tests/integration/test_ai_subtitle_flow.py`
    - 测试完整的AI字幕获取流程（使用真实测试视频）
    - 测试Cookie管理流程（mock BBDown登录）
    - 测试降级机制（字幕不可用时降级到ASR）
    - 测试CLI集成（所有新参数）
    - _Requirements: 5.1, 5.2, 9.1_

  - [ ]* 14.2 编写属性测试
    - **Property 18: Final Error Propagation**
    - **Property 19: Cookie Check in CLI**
    - **Property 21: Source Display in CLI**
    - **Validates: Requirements 2.5, 8.4, 9.1, 9.5, 11.4**

- [x] 15. 更新文档
  - [x] 15.1 更新README.md
    - 添加AI字幕支持说明
    - 添加Cookie管理说明
    - 添加BBDown登录使用指南
    - 添加新的CLI参数文档
    - 添加故障排除部分
    - _Requirements: 9.1, 9.2, 9.3, 9.4_

  - [x] 15.2 创建Cookie使用指南
    - 更新或创建`COOKIE_GUIDE.md`
    - 说明Cookie的作用和必要性
    - 说明如何使用BBDown登录
    - 说明Cookie文件位置和格式
    - 添加安全注意事项
    - 添加常见问题解答
    - _Requirements: 1.1, 1.2, 1.3, 7.1, 7.2_

- [ ] 16. Final Checkpoint - 完整功能验证
  - 运行所有测试套件确保通过
  - 手动测试完整的提取流程（有字幕视频）
  - 手动测试完整的提取流程（无字幕视频，降级到ASR）
  - 手动测试Cookie管理（登录、检查状态）
  - 验证所有CLI参数正常工作
  - 检查代码质量和文档完整性
  - 询问用户是否有问题或需要调整

## Notes

- 任务标记`*`为可选任务，可以跳过以加快MVP开发
- 每个任务都引用了具体的需求编号以确保可追溯性
- Checkpoint任务确保增量验证和用户反馈
- 属性测试验证通用正确性属性
- 单元测试验证具体示例和边界情况
- 所有实现使用Python语言（项目现有语言）
