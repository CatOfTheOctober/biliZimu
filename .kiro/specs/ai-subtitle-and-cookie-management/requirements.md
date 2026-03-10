# Requirements Document: B站AI字幕支持和Cookie管理

## Introduction

本文档定义了为B站视频文字提取系统添加AI字幕支持和自动Cookie管理功能的需求。当前系统使用BBDown获取字幕，但无法获取B站的AI字幕。通过分析SubBatch浏览器插件，发现B站提供了专门的AI字幕API。此外，某些视频（大会员内容、付费内容）需要Cookie才能访问字幕。本需求文档涵盖：(1) 调用B站播放器API获取AI字幕，(2) 集成BBDown登录功能管理Cookie，(3) 建立字幕获取优先级机制（播放器API → ASR）。

## Glossary

- **System**: B站视频文字提取系统（bilibili-extractor）
- **AuthManager**: 认证管理器组件，负责Cookie管理和登录
- **SubtitleFetcher**: 字幕获取器组件，负责协调字幕获取流程
- **BilibiliAPI**: B站API客户端组件，封装所有B站API调用
- **SubtitleParser**: 字幕解析器组件，解析不同格式的字幕数据
- **ASREngine**: 语音识别引擎组件，用于音频转文字
- **Cookie**: B站登录凭证，包含SESSDATA等字段
- **AI_Subtitle**: B站自动生成的字幕，通过专用API获取
- **Regular_Subtitle**: 用户上传或官方提供的普通字幕
- **TextSegment**: 文本片段数据结构，包含时间戳和文本内容
- **BVID**: B站视频ID，格式为BV开头的字符串
- **AID**: B站视频的数字ID
- **CID**: B站视频分P的ID
- **BBDown**: 第三方B站视频下载工具，支持二维码登录

## Requirements

### Requirement 1: Cookie管理

**User Story:** 作为用户，我希望系统能自动管理B站登录Cookie，这样我就可以访问需要登录才能获取的字幕内容。

#### Acceptance Criteria

1. WHEN THE System启动时 THEN THE AuthManager SHALL检查Cookie是否存在于配置文件或BBDown默认位置
2. WHEN Cookie文件存在 THEN THE AuthManager SHALL验证Cookie格式是否包含必需的SESSDATA字段
3. WHEN Cookie不存在或无效 THEN THE AuthManager SHALL提示用户登录并调用BBDown登录功能
4. WHEN BBDown登录成功 THEN THE AuthManager SHALL读取并保存Cookie文件路径
5. WHEN需要Cookie进行API调用 THEN THE AuthManager SHALL提供Cookie内容的字符串格式

### Requirement 2: B站API集成

**User Story:** 作为开发者，我希望系统能调用B站的各种API，这样我就可以获取视频信息和字幕数据。

#### Acceptance Criteria

1. WHEN提供BVID THEN THE BilibiliAPI SHALL调用视频信息API并返回AID和CID
2. WHEN提供AID和CID THEN THE BilibiliAPI SHALL调用播放器API并返回字幕列表
3. WHEN字幕列表包含AI字幕且URL为空 THEN THE BilibiliAPI SHALL调用AI字幕API获取下载URL
4. WHEN获取到字幕URL THEN THE BilibiliAPI SHALL下载字幕JSON数据
5. WHEN API返回错误 THEN THE BilibiliAPI SHALL抛出包含错误信息的异常
6. WHEN字幕URL是相对路径 THEN THE BilibiliAPI SHALL将其转换为完整的HTTPS URL

### Requirement 3: AI字幕识别和获取

**User Story:** 作为用户，我希望系统能自动识别并获取B站的AI字幕，这样我就可以获取没有人工字幕的视频的文字内容。

#### Acceptance Criteria

1. WHEN播放器API返回字幕列表 THEN THE SubtitleFetcher SHALL优先查找语言代码为'ai-zh'的字幕
2. WHEN找到AI字幕且subtitle_url为空 THEN THE SubtitleFetcher SHALL调用AI字幕专用API
3. WHEN AI字幕API返回URL THEN THE SubtitleFetcher SHALL下载该URL的字幕内容
4. WHEN AI字幕不可用 THEN THE SubtitleFetcher SHALL尝试获取其他可用字幕
5. WHEN所有字幕都不可用 THEN THE SubtitleFetcher SHALL抛出SubtitleNotFoundError异常

### Requirement 4: 字幕解析

**User Story:** 作为开发者，我希望系统能解析不同格式的字幕数据，这样我就可以统一处理AI字幕和普通字幕。

#### Acceptance Criteria

1. WHEN接收到字幕JSON数据 THEN THE SubtitleParser SHALL检测是AI字幕格式还是普通字幕格式
2. WHEN解析AI字幕 THEN THE SubtitleParser SHALL从body数组中提取from、to和content字段
3. WHEN解析普通字幕 THEN THE SubtitleParser SHALL从body数组中提取from、to和content字段
4. WHEN解析完成 THEN THE SubtitleParser SHALL返回TextSegment列表
5. FOR ALL TextSegment THEN THE SubtitleParser SHALL确保start_time小于end_time
6. FOR ALL TextSegment列表 THEN THE SubtitleParser SHALL按start_time升序排序

### Requirement 5: 字幕获取优先级

**User Story:** 作为用户，我希望系统能按优先级尝试不同的字幕获取方式，这样我就可以最大化获取字幕的成功率。

#### Acceptance Criteria

1. WHEN开始提取文字 THEN THE SubtitleFetcher SHALL首先尝试从B站API获取字幕
2. WHEN B站API获取失败 THEN THE SubtitleFetcher SHALL降级到ASR引擎
3. WHEN使用API获取字幕 THEN THE TextSegment的source字段 SHALL设置为'subtitle'
4. WHEN使用ASR获取文字 THEN THE TextSegment的source字段 SHALL设置为'asr'
5. FOR ALL提取操作 THEN THE System SHALL确保返回非空的TextSegment列表

### Requirement 6: 时间戳验证

**User Story:** 作为开发者，我希望所有文本片段都有有效的时间戳，这样我就可以确保输出数据的正确性。

#### Acceptance Criteria

1. FOR ALL TextSegment THEN THE System SHALL确保start_time小于end_time
2. FOR ALL相邻的TextSegment THEN THE System SHALL确保前一个的end_time小于等于后一个的start_time
3. WHEN解析字幕时间戳 THEN THE SubtitleParser SHALL正确转换秒数为浮点数
4. WHEN时间戳无效 THEN THE System SHALL抛出验证错误

### Requirement 7: Cookie安全

**User Story:** 作为用户，我希望我的Cookie信息被安全存储，这样我就可以保护我的账号安全。

#### Acceptance Criteria

1. WHEN保存Cookie文件 THEN THE AuthManager SHALL在Unix系统上设置文件权限为600
2. WHEN记录日志 THEN THE System SHALL不输出完整的Cookie内容
3. WHEN Cookie文件不存在 THEN THE AuthManager SHALL创建具有受限权限的新文件
4. WHEN读取Cookie THEN THE AuthManager SHALL验证文件权限是否安全

### Requirement 8: 错误处理和重试

**User Story:** 作为用户，我希望系统能处理网络错误和API失败，这样我就可以在不稳定的网络环境下使用系统。

#### Acceptance Criteria

1. WHEN API请求失败 THEN THE BilibiliAPI SHALL最多重试3次
2. WHEN重试时 THEN THE BilibiliAPI SHALL使用指数退避策略
3. WHEN收到429状态码 THEN THE BilibiliAPI SHALL等待后重试
4. WHEN所有重试都失败 THEN THE BilibiliAPI SHALL抛出BilibiliAPIError异常
5. WHEN网络超时 THEN THE BilibiliAPI SHALL在5秒连接超时和30秒读取超时后失败

### Requirement 9: CLI集成

**User Story:** 作为用户，我希望通过命令行使用新功能，这样我就可以方便地提取字幕。

#### Acceptance Criteria

1. WHEN用户运行提取命令 THEN THE CLI SHALL自动检查Cookie并在需要时提示登录
2. WHEN用户使用--login参数 THEN THE CLI SHALL强制触发登录流程
3. WHEN用户使用--check-cookie参数 THEN THE CLI SHALL显示Cookie状态信息
4. WHEN用户使用--cookie参数 THEN THE CLI SHALL使用指定的Cookie文件
5. WHEN提取完成 THEN THE CLI SHALL显示字幕来源（API或ASR）

### Requirement 10: 性能优化

**User Story:** 作为用户，我希望系统能快速获取字幕，这样我就可以提高工作效率。

#### Acceptance Criteria

1. WHEN多次请求相同视频信息 THEN THE BilibiliAPI SHALL使用缓存避免重复请求
2. WHEN进行HTTP请求 THEN THE BilibiliAPI SHALL使用连接池复用连接
3. WHEN处理大型字幕文件 THEN THE SubtitleParser SHALL使用流式处理减少内存占用
4. WHEN批量处理视频 THEN THE System SHALL实现请求速率限制避免被封禁
5. WHEN缓存达到上限 THEN THE System SHALL使用LRU策略清理旧缓存

### Requirement 11: 输入验证

**User Story:** 作为开发者，我希望系统能验证所有输入，这样我就可以防止注入攻击和系统错误。

#### Acceptance Criteria

1. WHEN接收BVID THEN THE System SHALL验证格式为BV开头加10个字母数字字符
2. WHEN接收文件路径 THEN THE System SHALL验证路径在允许的目录范围内
3. WHEN接收API响应 THEN THE System SHALL验证响应结构符合预期格式
4. WHEN验证失败 THEN THE System SHALL抛出包含详细信息的验证错误
5. FOR ALL用户输入 THEN THE System SHALL转义特殊字符防止注入

### Requirement 12: 日志记录

**User Story:** 作为开发者，我希望系统能记录详细的操作日志，这样我就可以调试问题和监控系统运行。

#### Acceptance Criteria

1. WHEN开始字幕获取 THEN THE System SHALL记录视频ID和获取方式
2. WHEN API调用失败 THEN THE System SHALL记录错误详情和响应内容
3. WHEN降级到ASR THEN THE System SHALL记录降级原因
4. WHEN Cookie操作 THEN THE System SHALL记录操作类型但不记录Cookie内容
5. FOR ALL关键操作 THEN THE System SHALL记录时间戳和执行结果
