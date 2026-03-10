# Requirements Document

## Introduction

B站视频文字提取系统是一个智能文本提取工具，能够从B站视频中提取文字内容。系统采用混合方案，优先使用官方字幕以获得最佳准确度和速度，在无官方字幕时自动降级到ASR语音识别（默认使用FunASR进行中文识别，可选Whisper进行多语言识别），并可选择性地使用OCR辅助校对硬字幕内容。

## Glossary

- **Text_Extractor**: 主系统，负责协调整个文字提取流程
- **Subtitle_Fetcher**: 字幕获取模块，负责检测和下载B站官方字幕。可使用BBDown工具的--sub-only参数直接下载字幕，或通过B站API获取
- **Video_Downloader**: 视频下载模块，主要使用BBDown（成熟的B站下载工具，支持多种API模式、多线程下载、Cookie认证），备用you-get或yt-dlp
- **Audio_Extractor**: 音频提取模块，使用ffmpeg从视频中提取音频，支持配置音频质量参数以优化处理速度
- **ASR_Engine**: 自动语音识别引擎，主要使用FunASR（阿里达摩院开源，专门针对中文优化）进行语音识别，备用Whisper（多语言支持）。FunASR提供更高的中文识别准确度（比Whisper高5-15%）、更快的推理速度（比Whisper快2-3倍）、自动标点符号添加和词级别精确时间戳。支持标准模型、INT8量化模型（速度提升2-3倍）和ONNX Runtime（速度提升3-4倍）以优化CPU性能
- **OCR_Engine**: 光学字符识别引擎，使用PaddleOCR或Tesseract识别视频中的硬字幕
- **Official_Subtitle**: B站视频的官方字幕文件（如CC字幕、UP主上传的字幕）
- **Hard_Subtitle**: 直接嵌入在视频画面中的字幕
- **Bilibili_URL**: B站视频的有效URL地址
- **Text_Output**: 提取的文本内容，包含时间戳和文字信息
- **Cookie_File**: 可选的B站登录凭证文件，用于访问大会员视频、付费内容或避免频率限制

## Requirements

### Requirement 1: 接受B站视频URL输入

**User Story:** 作为用户，我希望能够输入B站视频URL，以便系统能够识别并处理该视频

#### Acceptance Criteria

1. WHEN 用户提供一个有效的Bilibili_URL，THE Text_Extractor SHALL 验证URL格式的有效性
2. THE Text_Extractor SHALL 支持标准B站视频URL格式（包括 bilibili.com/video/BV 和 b23.tv 短链接）
3. IF 提供的URL格式无效，THEN THE Text_Extractor SHALL 返回明确的错误信息
4. WHEN URL验证成功，THE Text_Extractor SHALL 提取视频ID用于后续处理

#### Correctness Properties

- **Invariant**: 对于任何有效的Bilibili_URL，提取的视频ID应保持一致，无论URL格式如何变化
- **Error Condition**: 所有无效URL输入应被正确识别并返回错误，不应导致系统崩溃

### Requirement 2: 检测和获取官方字幕

**User Story:** 作为用户，我希望系统优先使用官方字幕，以便获得最准确和最快的文字提取结果

#### Acceptance Criteria

1. WHEN 接收到视频ID，THE Subtitle_Fetcher SHALL 首先检查该视频是否存在Official_Subtitle
2. WHEN Official_Subtitle存在，THE Subtitle_Fetcher SHALL 使用BBDown的--sub-only参数下载所有可用的字幕文件
3. WHERE 存在多个字幕语言选项，THE Subtitle_Fetcher SHALL 优先选择中文字幕
4. WHERE 提供了Cookie_File，THE Subtitle_Fetcher SHALL 使用Cookie进行认证以访问大会员或付费内容
5. THE Subtitle_Fetcher SHALL 解析字幕文件格式（支持SRT、JSON、XML等常见格式）
6. WHEN 字幕解析成功，THE Subtitle_Fetcher SHALL 将字幕内容转换为标准化的Text_Output格式
7. IF 字幕下载或解析失败，THEN THE Subtitle_Fetcher SHALL 记录错误并通知Text_Extractor使用备用方案

#### Correctness Properties

- **Round Trip**: 解析字幕文件后生成的Text_Output应能够重新格式化为有效的字幕文件格式
- **Invariant**: 字幕时间戳的顺序在解析前后应保持一致（start_time <= end_time，且时间戳单调递增）
- **Model Based**: 字幕解析结果应与标准字幕解析库的输出一致

### Requirement 3: 下载视频文件

**User Story:** 作为用户，当视频没有官方字幕时，我希望系统能够下载视频文件，以便进行后续的ASR或OCR处理

#### Acceptance Criteria

1. WHEN Official_Subtitle不存在，THE Video_Downloader SHALL 使用BBDown下载视频
2. WHERE 提供了Cookie_File，THE Video_Downloader SHALL 使用Cookie进行认证
3. THE Video_Downloader SHALL 选择适当的视频质量以平衡文件大小和ASR准确度
4. THE Video_Downloader SHALL 使用BBDown的多线程下载功能以提高下载速度
5. WHEN 下载开始，THE Video_Downloader SHALL 提供下载进度反馈
6. THE Video_Downloader SHALL 将视频保存到指定的临时目录
7. IF BBDown下载失败，THEN THE Video_Downloader SHALL 尝试使用备用下载工具（you-get或yt-dlp）
8. IF 所有下载尝试失败，THEN THE Video_Downloader SHALL 返回详细的错误信息

#### Correctness Properties

- **Idempotence**: 对同一视频URL多次调用下载操作应产生相同的结果文件
- **Error Condition**: 网络错误、权限错误、视频不存在等异常情况应被正确处理并返回相应错误码

### Requirement 4: 提取音频流

**User Story:** 作为用户，我希望系统能够从下载的视频中提取音频，以便进行语音识别

#### Acceptance Criteria

1. WHEN 视频文件下载完成，THE Audio_Extractor SHALL 使用ffmpeg提取音频流
2. THE Audio_Extractor SHALL 将音频转换为ASR_Engine支持的格式（WAV格式，16kHz采样率，单声道）
3. WHERE 用户配置了音频质量优化参数，THE Audio_Extractor SHALL 使用指定的码率（如32kbps）以加快后续处理速度
4. THE Audio_Extractor SHALL 保留音频的完整时长信息
5. WHEN 音频提取完成，THE Audio_Extractor SHALL 验证音频文件的完整性
6. IF 音频提取失败，THEN THE Audio_Extractor SHALL 返回错误信息并保留原始视频文件用于调试

#### Correctness Properties

- **Invariant**: 提取的音频时长应与原视频时长一致（允许±1秒的误差）
- **Round Trip**: 音频文件应能被标准音频播放器正常播放
- **Error Condition**: 损坏的视频文件应被检测并返回明确的错误信息

### Requirement 5: 执行语音识别

**User Story:** 作为用户，我希望系统能够使用ASR技术将音频转换为文字，以便在没有官方字幕时仍能获取视频内容

#### Acceptance Criteria

1. WHEN 音频文件准备就绪，THE ASR_Engine SHALL 默认使用FunASR模型进行中文语音识别
2. THE ASR_Engine SHALL 使用paraformer-zh模型进行语音识别，配合fsmn-vad进行语音活动检测和ct-punc进行标点预测
3. THE ASR_Engine SHALL 生成带词级别精确时间戳的文字转录结果
4. THE ASR_Engine SHALL 自动为识别结果添加标点符号
5. WHERE 用户通过配置选择使用Whisper引擎，THE ASR_Engine SHALL 切换到Whisper进行多语言识别
6. WHERE 用户指定了语言参数且使用Whisper，THE ASR_Engine SHALL 使用指定语言进行识别
7. THE ASR_Engine SHALL 提供识别进度反馈
8. WHEN 识别完成，THE ASR_Engine SHALL 将结果转换为标准化的Text_Output格式
9. IF 音频质量过低导致识别失败，THEN THE ASR_Engine SHALL 返回警告信息和部分识别结果

#### Correctness Properties

- **Metamorphic**: 对于清晰的音频，ASR识别的文字数量应与音频时长成正比关系
- **Invariant**: 生成的时间戳应单调递增且覆盖整个音频时长
- **Model Based**: 对于标准中文测试音频，使用FunASR的识别准确率应比Whisper高5-15%，推理速度应快2-3倍

### Requirement 6: OCR辅助校对（可选功能）

**User Story:** 作为用户，当视频包含硬字幕时，我希望系统能够使用OCR辅助校对ASR结果，以便提高文字提取的准确度

#### Acceptance Criteria

1. WHERE OCR功能启用，THE OCR_Engine SHALL 检测视频帧中是否存在Hard_Subtitle
2. WHEN Hard_Subtitle被检测到，THE OCR_Engine SHALL 在关键帧上执行文字识别
3. THE OCR_Engine SHALL 使用PaddleOCR或Tesseract进行文字识别
4. THE OCR_Engine SHALL 将OCR结果与ASR结果进行时间戳对齐
5. WHEN OCR和ASR结果存在差异，THE OCR_Engine SHALL 标记差异位置供用户审核
6. THE Text_Extractor SHALL 提供合并策略选项（优先ASR、优先OCR、或人工选择）

#### Correctness Properties

- **Confluence**: OCR和ASR结果的合并顺序不应影响最终输出的时间戳顺序
- **Metamorphic**: OCR识别的文字数量应不超过视频帧数与平均字幕显示时长的乘积
- **Error Condition**: 无字幕的视频帧应被正确识别，不应产生虚假的OCR结果

### Requirement 7: 输出标准化文本

**User Story:** 作为用户，我希望系统能够输出统一格式的文本结果，以便我能够方便地使用和处理提取的内容

#### Acceptance Criteria

1. THE Text_Extractor SHALL 将所有提取的文字内容格式化为Text_Output
2. THE Text_Extractor SHALL 在输出中包含时间戳信息（开始时间和结束时间）
3. THE Text_Extractor SHALL 支持多种输出格式（纯文本、SRT、JSON、Markdown）
4. WHERE 用户指定输出格式，THE Text_Extractor SHALL 使用指定格式
5. WHERE 用户未指定输出格式，THE Text_Extractor SHALL 默认使用SRT格式
6. THE Text_Extractor SHALL 在输出中包含元数据（视频URL、提取方法、提取时间）
7. WHEN 输出生成完成，THE Text_Extractor SHALL 验证输出文件的格式正确性

#### Correctness Properties

- **Round Trip**: 生成的SRT或JSON格式输出应能被标准解析器正确解析并还原为等价的数据结构
- **Invariant**: 输出文本的时间戳顺序应保持单调递增
- **Model Based**: 输出格式应符合相应格式的标准规范（如SRT规范、JSON Schema）

### Requirement 8: 错误处理和日志记录

**User Story:** 作为用户，当系统遇到错误时，我希望能够获得清晰的错误信息和日志，以便我能够理解问题并采取相应措施

#### Acceptance Criteria

1. WHEN 任何模块发生错误，THE Text_Extractor SHALL 记录详细的错误日志
2. THE Text_Extractor SHALL 为每个处理步骤记录开始时间、结束时间和状态
3. IF 某个步骤失败，THEN THE Text_Extractor SHALL 记录失败原因和上下文信息
4. THE Text_Extractor SHALL 提供不同的日志级别（DEBUG、INFO、WARNING、ERROR）
5. WHERE 用户指定日志级别，THE Text_Extractor SHALL 使用指定级别
6. THE Text_Extractor SHALL 将日志输出到文件和控制台
7. WHEN 处理完成，THE Text_Extractor SHALL 生成处理摘要报告

#### Correctness Properties

- **Invariant**: 每个处理步骤的开始日志应有对应的结束日志（成功或失败）
- **Error Condition**: 所有异常情况应被捕获并记录，不应导致程序崩溃而不留下日志

### Requirement 9: 资源清理和管理

**User Story:** 作为用户，我希望系统能够自动清理临时文件，以便不会占用过多的磁盘空间

#### Acceptance Criteria

1. WHEN 文字提取完成，THE Text_Extractor SHALL 删除临时下载的视频文件
2. WHEN 文字提取完成，THE Text_Extractor SHALL 删除临时提取的音频文件
3. WHERE 用户指定保留临时文件，THE Text_Extractor SHALL 保留所有中间文件
4. IF 处理过程中发生错误，THEN THE Text_Extractor SHALL 仍然执行资源清理
5. THE Text_Extractor SHALL 提供临时文件存储位置的配置选项
6. THE Text_Extractor SHALL 在开始处理前检查磁盘空间是否充足

#### Correctness Properties

- **Idempotence**: 多次调用清理操作应是安全的，不应产生错误
- **Invariant**: 清理操作后，临时目录中不应残留当前任务的文件
- **Error Condition**: 文件删除失败应被记录但不应阻止程序继续执行

### Requirement 10: 性能和进度反馈

**User Story:** 作为用户，我希望能够看到处理进度，以便了解任务的执行状态和预计完成时间

#### Acceptance Criteria

1. WHEN 处理开始，THE Text_Extractor SHALL 显示当前执行的步骤
2. WHILE 下载视频，THE Text_Extractor SHALL 显示下载进度百分比
3. WHILE 执行ASR识别，THE Text_Extractor SHALL 显示识别进度
4. THE Text_Extractor SHALL 估算并显示剩余处理时间
5. WHEN 每个主要步骤完成，THE Text_Extractor SHALL 显示该步骤的耗时
6. THE Text_Extractor SHALL 在处理结束时显示总耗时统计

#### Correctness Properties

- **Invariant**: 进度百分比应单调递增，范围在0-100之间
- **Metamorphic**: 对于相似时长的视频，处理时间应大致成正比关系
- **Model Based**: 进度估算的误差应在合理范围内（±20%）

### Requirement 11: 配置和可扩展性

**User Story:** 作为用户，我希望能够配置系统的行为参数，以便根据不同场景优化处理效果

#### Acceptance Criteria

1. THE Text_Extractor SHALL 支持通过配置文件设置系统参数
2. THE Text_Extractor SHALL 支持通过命令行参数覆盖配置文件设置
3. THE Text_Extractor SHALL 提供默认配置以确保开箱即用
4. WHERE 用户指定ASR引擎类型，THE Text_Extractor SHALL 使用指定引擎（FunASR或Whisper）
5. WHERE 用户未指定ASR引擎，THE Text_Extractor SHALL 默认使用FunASR
6. WHERE 用户指定FunASR模型，THE Text_Extractor SHALL 使用指定模型（如paraformer-zh）
7. WHERE 用户指定Whisper模型大小，THE Text_Extractor SHALL 使用指定模型
8. WHERE 用户指定视频下载质量，THE Text_Extractor SHALL 使用指定质量
9. THE Text_Extractor SHALL 验证配置参数的有效性
10. IF 配置参数无效，THEN THE Text_Extractor SHALL 使用默认值并发出警告

#### Correctness Properties

- **Invariant**: 配置参数的验证规则应保持一致，相同的配置应产生相同的验证结果
- **Error Condition**: 无效的配置应被拒绝并提供清晰的错误信息，不应导致运行时错误

### Requirement 12: 批量处理支持

**User Story:** 作为用户，我希望能够批量处理多个视频，以便提高工作效率

#### Acceptance Criteria

1. THE Text_Extractor SHALL 接受包含多个Bilibili_URL的输入列表
2. WHEN 处理多个视频，THE Text_Extractor SHALL 按顺序处理每个视频
3. THE Text_Extractor SHALL 为每个视频生成独立的Text_Output文件
4. IF 某个视频处理失败，THEN THE Text_Extractor SHALL 继续处理列表中的其他视频
5. WHEN 批量处理完成，THE Text_Extractor SHALL 生成汇总报告
6. THE Text_Extractor SHALL 在汇总报告中列出成功和失败的视频数量

#### Correctness Properties

- **Confluence**: 批量处理的顺序不应影响每个视频的处理结果
- **Invariant**: 批量处理的成功数量加失败数量应等于输入视频总数
- **Idempotence**: 对失败的视频重新处理应产生一致的结果

