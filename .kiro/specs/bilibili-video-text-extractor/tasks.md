# Implementation Plan: Bilibili Video Text Extractor

## Overview

本实现计划将B站视频文字提取系统分为8个阶段，从基础设施搭建到完整功能实现。优先实现MVP核心功能（官方字幕提取），然后逐步添加ASR、CPU优化和扩展功能。每个任务都包含具体的实现目标和对应的需求引用。

## Tasks

- [x] 1. 项目基础设施搭建
  - 创建项目目录结构和基础文件
  - 设置Python包配置（pyproject.toml, setup.py）
  - 配置开发工具（black, mypy, pytest）
  - _Requirements: 11.1, 11.9_

- [x] 2. 核心数据模型和配置系统
  - [x] 2.1 实现数据模型类
    - 在`src/bilibili_extractor/core/models.py`中实现VideoInfo, TextSegment, ExtractionResult数据类
    - 使用dataclass装饰器，添加类型注解
    - _Requirements: 7.1, 7.2_
  
  - [x] 2.2 实现配置管理系统
    - 在`src/bilibili_extractor/core/config.py`中实现Config数据类
    - 实现ConfigLoader类，支持从YAML文件和命令行参数加载配置
    - 实现配置验证逻辑
    - _Requirements: 11.1, 11.9, 11.10_
  
  - [ ]* 2.3 编写配置系统的属性测试
    - **Property 38: 配置验证应拒绝无效值**
    - **Property 39: 命令行参数应覆盖配置文件**
    - **Property 40: 缺失配置使用默认值**
    - **Validates: Requirements 11.9, 11.10**

- [x] 3. 日志和资源管理工具
  - [x] 3.1 实现日志系统
    - 在`src/bilibili_extractor/utils/logger.py`中实现Logger类
    - 配置日志格式、级别和输出目标（控制台+文件）
    - _Requirements: 8.1, 8.2, 8.4, 8.5, 8.6_
  
  - [x] 3.2 实现资源管理器
    - 在`src/bilibili_extractor/utils/resource_manager.py`中实现ResourceManager类
    - 实现文件注册、清理和磁盘空间检查功能
    - 使用上下文管理器确保清理
    - _Requirements: 9.1, 9.2, 9.4, 9.5, 9.6_
  
  - [ ]* 3.3 编写资源管理的属性测试
    - **Property 24: cleanup()应是幂等的**
    - **Property 25: cleanup()后文件应被删除**
    - **Property 26: 清理失败不应阻止程序执行**
    - **Validates: Requirements 9.1, 9.2, 9.4**


- [x] 4. URL验证模块（MVP核心）
  - [x] 4.1 实现URL验证器
    - 在`src/bilibili_extractor/modules/url_validator.py`中实现URLValidator类
    - 实现validate()方法：支持bilibili.com/video/BV*, b23.tv/*, av号格式
    - 实现extract_video_id()方法：使用正则表达式提取视频ID
    - 实现normalize_url()方法：处理短链接重定向
    - _Requirements: 1.1, 1.2, 1.3, 1.4_
  
  - [ ]* 4.2 编写URL验证的单元测试
    - 测试各种有效和无效URL格式
    - 测试短链接处理
    - 测试错误情况
    - _Requirements: 1.1, 1.2, 1.3_
  
  - [ ]* 4.3 编写URL验证的属性测试
    - **Property 1: 对于有效URL，extract_video_id()应返回一致的video_id**
    - **Property 2: validate()返回True当且仅当extract_video_id()不抛出异常**
    - **Validates: Requirements 1.1, 1.3**

- [x] 5. 字幕获取模块（MVP核心）
  - [x] 5.1 实现BBDown字幕下载功能
    - 在`src/bilibili_extractor/modules/subtitle_fetcher.py`中实现SubtitleFetcher类
    - 实现download_with_bbdown()：使用`BBDown <url> --sub-only`命令下载字幕
    - 解析BBDown输出判断是否有字幕（捕获"不存在字幕"等提示）
    - 支持Cookie认证（--cookie参数）
    - 在临时目录查找下载的字幕文件（SRT/JSON/XML格式）
    - 抛出SubtitleNotFoundError异常当字幕不存在时
    - _Requirements: 2.1, 2.2, 2.4_
  
  - [x] 5.2 实现字幕解析功能
    - 实现parse_subtitle()方法：支持SRT、JSON、XML格式
    - 将字幕内容转换为TextSegment列表
    - 优先选择中文字幕
    - _Requirements: 2.3, 2.5, 2.6_
  
  - [ ]* 5.3 编写字幕解析的单元测试
    - 使用fixtures测试SRT、JSON、XML格式解析
    - 测试多语言字幕选择逻辑
    - 测试错误处理
    - _Requirements: 2.5, 2.6, 2.7_
  
  - [ ]* 5.4 编写字幕模块的属性测试
    - **Property 3: 解析后的segments时间戳应单调递增**
    - **Property 4: 每个segment的start_time < end_time**
    - **Property 5: 解析SRT后重新生成SRT应保持时间戳一致**
    - **Validates: Requirements 2.5, 2.6**

- [x] 6. 输出格式化模块（MVP核心）
  - [x] 6.1 实现输出格式化器
    - 在`src/bilibili_extractor/modules/output_formatter.py`中实现OutputFormatter类
    - 实现to_srt()：生成标准SRT格式
    - 实现to_json()：生成包含元数据的JSON格式
    - 实现to_txt()：生成纯文本格式
    - 实现to_markdown()：生成Markdown格式
    - 实现validate_format()：验证输出格式正确性
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7_
  
  - [ ]* 6.2 编写输出格式化的单元测试
    - 测试各种输出格式的生成
    - 测试格式验证功能
    - _Requirements: 7.3, 7.4, 7.7_
  
  - [ ]* 6.3 编写输出格式化的属性测试
    - **Property 20: SRT输出应能被标准SRT解析器解析**
    - **Property 21: JSON输出应符合定义的schema**
    - **Property 22: 格式转换应保持时间戳信息不丢失**
    - **Property 23: 重新解析输出文件应得到等价的数据结构**
    - **Validates: Requirements 7.2, 7.3, 7.7**


- [x] 7. MVP主控制器和CLI
  - [x] 7.1 实现主控制器（仅字幕提取）
    - 在`src/bilibili_extractor/core/extractor.py`中实现TextExtractor类
    - 实现extract()方法：协调URL验证、字幕获取、输出格式化流程
    - 实现两阶段处理逻辑：先尝试BBDown --sub-only，失败则准备后续ASR流程
    - 实现错误处理和日志记录
    - 实现资源清理（使用ResourceManager）
    - _Requirements: 1.1, 2.1, 2.2, 7.1, 8.1, 8.2, 9.1_
  
  - [x] 7.2 实现基础CLI
    - 在`src/bilibili_extractor/cli.py`中实现命令行参数解析
    - 在`src/bilibili_extractor/__main__.py`中实现CLI入口
    - 支持基本参数：url, --config, --output, --format
    - 实现进度显示和摘要报告
    - _Requirements: 10.1, 10.2, 10.5, 10.6_
  
  - [ ]* 7.3 编写MVP集成测试
    - 测试完整的字幕提取流程
    - 测试错误处理和资源清理
    - _Requirements: 1.1, 2.1, 7.1, 9.1_
  
  - [ ]* 7.4 编写主控制器的属性测试
    - **Property 29: 无论成功或失败，cleanup()都应被调用**
    - **Property 27: 每个处理步骤的开始日志应有对应的结束日志**
    - **Validates: Requirements 8.1, 9.1, 9.4**

- [x] 8. Checkpoint - MVP功能验证
  - 确保所有测试通过
  - 手动测试字幕提取功能
  - 询问用户是否有问题或需要调整

- [x] 9. 视频下载模块
  - [x] 9.1 实现BBDown视频下载器
    - 在`src/bilibili_extractor/modules/video_downloader.py`中实现VideoDownloader类
    - 实现download_with_bbdown()：使用`BBDown <url>`命令下载完整视频
    - 支持质量选择（-q参数，如-q 80表示1080P）
    - 支持Cookie认证（--cookie参数）
    - 支持多线程下载（-mt参数）
    - 解析BBDown输出获取下载进度
    - 实现进度回调机制（解析百分比和速度信息）
    - 返回下载的视频文件路径
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.7, 3.8_
  
  - [ ]* 9.2 编写视频下载的单元测试
    - 测试BBDown命令构建（URL、质量、Cookie参数）
    - 测试进度解析（百分比、速度、ETA）
    - 测试错误处理（网络错误、权限错误）
    - _Requirements: 3.1, 3.5, 3.7_
  
  - [ ]* 9.3 编写视频下载的属性测试
    - **Property 6: 对同一video_id多次下载应得到相同的文件**
    - **Property 8: 下载进度应从0%到100%单调递增**
    - **Validates: Requirements 3.1, 3.5**

- [x] 10. 音频提取模块
  - [x] 10.1 实现音频提取器
    - 在`src/bilibili_extractor/modules/audio_extractor.py`中实现AudioExtractor类
    - 实现extract()方法：使用ffmpeg-python提取音频
    - 配置音频参数：16kHz采样率，单声道，WAV格式
    - 实现get_audio_duration()：获取音频时长
    - 实现validate_audio()：验证音频文件完整性
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6_
  
  - [ ]* 10.2 编写音频提取的单元测试
    - 测试音频提取参数
    - 测试时长获取
    - 测试文件验证
    - _Requirements: 4.1, 4.2, 4.5_
  
  - [ ]* 10.3 编写音频提取的属性测试
    - **Property 9: 提取的音频时长应与视频时长一致（±1秒）**
    - **Property 10: 音频文件应能被标准音频库读取**
    - **Property 11: 损坏的视频文件应返回明确错误**
    - **Validates: Requirements 4.4, 4.5, 4.6**


- [x] 11. ASR引擎基础实现
  - [x] 11.1 实现ASR引擎抽象层
    - 在`src/bilibili_extractor/modules/asr_engine.py`中实现ASREngine抽象基类
    - 定义transcribe()抽象方法
    - _Requirements: 5.1_
  
  - [x] 11.2 实现FunASR引擎（标准模型）
    - 实现FunASREngine类，继承ASREngine
    - 集成funasr库，使用paraformer-zh模型
    - 配置fsmn-vad（语音活动检测）和ct-punc（标点预测）
    - 实现transcribe()方法：返回带时间戳和置信度的TextSegment列表
    - 实现进度回调机制
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.7, 5.8_
  
  - [x] 11.3 实现Whisper引擎
    - 实现WhisperEngine类，继承ASREngine
    - 集成openai-whisper库
    - 支持模型大小选择和语言指定
    - 实现transcribe()方法
    - _Requirements: 5.5, 5.6, 5.7, 5.8_
  
  - [ ]* 11.4 编写ASR引擎的单元测试
    - 使用测试音频文件测试FunASR和Whisper
    - 测试进度回调
    - 测试错误处理
    - _Requirements: 5.1, 5.7, 5.9_
  
  - [ ]* 11.5 编写ASR引擎的属性测试
    - **Property 12: 识别结果的时间戳应单调递增**
    - **Property 13: 所有时间戳应在[0, audio_duration]范围内**
    - **Property 15: 识别进度应从0%到100%单调递增**
    - **Property 16: 空音频文件应返回空列表而非错误**
    - **Validates: Requirements 5.3, 5.7, 5.9**

- [x] 12. 集成ASR到主控制器
  - [x] 12.1 扩展主控制器支持ASR
    - 修改TextExtractor.extract()：实现完整的两阶段处理流程
    - 阶段1：尝试BBDown --sub-only下载字幕，成功则直接返回
    - 阶段2：字幕不存在时，使用BBDown下载完整视频→音频提取→ASR识别
    - 实现_create_asr_engine()：根据配置创建ASR引擎
    - 实现自动降级策略：捕获SubtitleNotFoundError后自动切换到ASR流程
    - _Requirements: 2.7, 3.1, 4.1, 5.1_
  
  - [ ]* 12.2 编写ASR集成测试
    - 测试完整的ASR流程：URL → 视频下载 → 音频提取 → ASR → 输出
    - 测试降级策略
    - _Requirements: 2.7, 5.1, 7.1_
  
  - [ ]* 12.3 编写错误处理的属性测试
    - **Property 32: 所有异常应被捕获并记录**
    - **Property 33: 用户可见的错误消息应清晰且可操作**
    - **Property 34: 系统不应因单个模块失败而完全崩溃**
    - **Validates: Requirements 8.1, 8.3**

- [x] 13. Checkpoint - ASR功能验证
  - 确保所有测试通过
  - 手动测试ASR识别功能
  - 询问用户是否有问题或需要调整


- [x] 14. CPU优化 - INT8量化
  - [x] 14.1 实现INT8量化支持
    - 修改FunASREngine：添加quantize参数
    - 配置FunASR使用INT8量化模型
    - 在Config中添加use_int8配置项
    - _Requirements: 5.1, 11.4, 11.5_
  
  - [ ]* 14.2 编写INT8量化的性能测试
    - 对比标准模型和INT8模型的处理速度
    - 测量准确率差异
    - _Requirements: 5.1, 11.4_
  
  - [ ]* 14.3 编写INT8量化的属性测试
    - **Property 35: INT8量化不应显著降低识别准确率（<5%）**
    - **Property 37: 处理时间应与视频时长成正比**
    - **Validates: Requirements 5.1, 10.6**

- [x] 15. CPU优化 - ONNX Runtime
  - [x] 15.1 实现ONNX Runtime支持
    - 修改FunASREngine：添加use_onnx参数
    - 配置FunASR使用ONNX Runtime加速
    - 在Config中添加use_onnx配置项
    - _Requirements: 5.1, 11.4, 11.5_
  
  - [ ]* 15.2 编写ONNX Runtime的性能测试
    - 对比标准模型、INT8和ONNX的处理速度
    - 测量内存使用
    - _Requirements: 5.1, 11.4_
  
  - [ ]* 15.3 编写性能相关的属性测试
    - **Property 36: 内存使用应随视频时长线性增长**
    - **Property 14: 对于清晰中文音频，FunASR准确率应高于Whisper**
    - **Validates: Requirements 5.1, 10.6**

- [x] 16. 批量处理功能
  - [x] 16.1 实现批量处理
    - 在TextExtractor中实现extract_batch()方法
    - 支持从文件读取URL列表
    - 实现单个失败不影响其他视频的错误处理
    - 生成批量处理汇总报告
    - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5, 12.6_
  
  - [x] 16.2 扩展CLI支持批量处理
    - 添加--batch参数：接受URL列表文件
    - 实现批量处理的进度显示
    - 实现汇总报告输出
    - _Requirements: 12.1, 12.5, 12.6_
  
  - [ ]* 16.3 编写批量处理的集成测试
    - 测试批量处理多个视频
    - 测试部分失败场景
    - 测试汇总报告生成
    - _Requirements: 12.2, 12.3, 12.4_
  
  - [ ]* 16.4 编写批量处理的属性测试
    - **Property 30: 批量处理中单个失败不应影响其他视频**
    - **Property 31: 相同URL的多次提取应产生一致的结果**
    - **Validates: Requirements 12.4, 12.5**

- [x] 17. Checkpoint - 核心功能完成
  - 确保所有核心功能测试通过
  - 验证CPU优化效果
  - 验证批量处理功能
  - 询问用户是否继续实现可选功能（OCR）


- [ ] 18. OCR引擎（可选功能）
  - [ ] 18.1 实现OCR引擎基础功能
    - 在`src/bilibili_extractor/modules/ocr_engine.py`中实现OCREngine类
    - 实现detect_subtitle_region()：检测视频中的字幕区域
    - 实现extract_text_from_frames()：从关键帧提取文字
    - 集成PaddleOCR库
    - _Requirements: 6.1, 6.2, 6.3_
  
  - [ ] 18.2 实现OCR和ASR结果合并
    - 实现merge_with_asr()方法：时间戳对齐和结果合并
    - 实现合并策略（优先ASR、优先OCR、标记差异）
    - _Requirements: 6.4, 6.5, 6.6_
  
  - [ ] 18.3 集成OCR到主控制器
    - 修改TextExtractor：添加OCR处理流程
    - 在Config中添加enable_ocr和ocr_engine配置项
    - _Requirements: 6.1, 6.6_
  
  - [ ]* 18.4 编写OCR的单元测试
    - 测试字幕区域检测
    - 测试文字提取
    - 测试结果合并
    - _Requirements: 6.2, 6.3, 6.4_
  
  - [ ]* 18.5 编写OCR的属性测试
    - **Property 17: OCR结果的时间戳应对应实际帧时间**
    - **Property 18: 合并后的segments时间戳应保持单调递增**
    - **Property 19: 无字幕帧不应产生OCR结果**
    - **Validates: Requirements 6.2, 6.4, 6.5**

- [x] 19. CLI完善和用户体验优化
  - [x] 19.1 完善CLI参数
    - 添加所有配置选项的命令行参数
    - 实现--version参数
    - 优化帮助信息
    - _Requirements: 11.2, 11.3_
  
  - [x] 19.2 实现进度显示
    - 在`src/bilibili_extractor/utils/progress.py`中实现进度条
    - 实现实时进度更新
    - 实现剩余时间估算
    - _Requirements: 10.1, 10.2, 10.3, 10.4_
  
  - [x] 19.3 优化输出和报告
    - 实现详细的处理摘要报告
    - 实现步骤耗时统计
    - 优化错误消息的可读性
    - _Requirements: 10.5, 10.6, 8.7_
  
  - [ ]* 19.4 编写CLI的属性测试
    - **Property 41: CLI应返回适当的退出码（0=成功，非0=失败）**
    - **Property 42: 进度显示应实时更新**
    - **Property 43: 错误消息应包含可操作的建议**
    - **Validates: Requirements 10.1, 10.4, 8.3**


- [x] 20. 文档编写
  - [x] 20.1 编写用户文档
    - 创建`docs/README.md`：项目概述和快速开始
    - 创建`docs/installation.md`：详细安装说明
    - 说明外部工具依赖：BBDown（必需）、FFmpeg（必需）
    - 说明Python依赖：FunASR、Whisper、PaddleOCR（可选）
    - 创建`docs/usage.md`：使用示例和配置说明
    - 包含常见问题和故障排除
    - _Requirements: 11.1_
  
  - [x] 20.2 编写API文档
    - 创建`docs/api.md`：核心类和方法的API文档
    - 包含代码示例
    - 文档化所有公共接口
    - _Requirements: 11.1_
  
  - [x] 20.3 编写项目README
    - 创建根目录`README.md`
    - 包含功能特性、安装、快速开始、示例
    - 添加徽章（版本、测试状态、覆盖率）
    - _Requirements: 11.1_

- [ ] 21. 完整测试套件和质量保证
  - [ ]* 21.1 补充缺失的单元测试
    - 确保所有模块都有单元测试
    - 达到80%以上的代码覆盖率
    - _Requirements: 8.1_
  
  - [ ]* 21.2 补充集成测试
    - 测试所有主要工作流程
    - 测试错误恢复场景
    - 测试资源清理
    - _Requirements: 8.1, 9.4_
  
  - [ ]* 21.3 运行完整的属性测试套件
    - 验证所有45个正确性属性
    - 使用hypothesis生成测试用例
    - 修复发现的问题
    - _Requirements: All_
  
  - [ ]* 21.4 性能基准测试
    - 测试不同模型配置的性能
    - 测试不同视频时长的处理时间
    - 测试内存使用情况
    - 生成性能报告
    - _Requirements: 10.6, 11.4, 11.5_

- [x] 22. 打包和发布准备
  - [x] 22.1 配置打包
    - 完善pyproject.toml和setup.py
    - 配置核心依赖：ffmpeg-python
    - 配置可选依赖：funasr（ASR）、openai-whisper（ASR）、paddleocr（OCR）
    - 说明外部工具要求：BBDown、FFmpeg
    - 配置入口点
    - _Requirements: 11.1_
  
  - [x] 22.2 创建默认配置文件
    - 创建`config/default_config.yaml`
    - 包含所有配置项的说明
    - _Requirements: 11.1, 11.3_
  
  - [x] 22.3 准备发布
    - 创建requirements.txt和requirements-dev.txt
    - 添加LICENSE文件
    - 添加CHANGELOG.md
    - _Requirements: 11.1_

- [ ] 23. 最终验证和优化
  - [ ] 23.1 端到端测试
    - 测试真实B站视频的提取
    - 测试各种场景（有字幕、无字幕、大会员内容）
    - 验证输出质量
    - _Requirements: All_
  
  - [ ] 23.2 性能优化
    - 分析性能瓶颈
    - 优化关键路径
    - 减少内存占用
    - _Requirements: 10.6, 11.4_
  
  - [ ] 23.3 代码质量检查
    - 运行black格式化代码
    - 运行mypy类型检查
    - 修复所有警告
    - _Requirements: 11.1_

- [x] 24. Final Checkpoint - 项目完成
  - 确保所有测试通过
  - 确保文档完整
  - 确保代码质量达标
  - 询问用户是否准备发布

## Notes

- 任务标记`*`的为可选测试任务，可以跳过以加快MVP开发
- 每个任务都引用了具体的需求条款以确保可追溯性
- Checkpoint任务用于阶段性验证和用户反馈
- 属性测试任务明确标注了要验证的属性编号和对应的需求
- 优先实现MVP核心功能（任务1-8），然后逐步添加ASR和扩展功能
- CPU优化（INT8和ONNX）是核心需求，在任务14-15中实现
- OCR功能是可选的，在任务18中实现
- 45个正确性属性分布在各个模块的属性测试任务中

## Implementation Strategy

1. **Phase 1 (Tasks 1-8)**: MVP核心 - 官方字幕提取和基础输出
2. **Phase 2 (Tasks 9-13)**: ASR集成 - 视频下载、音频提取、语音识别
3. **Phase 3 (Tasks 14-15)**: CPU优化 - INT8量化和ONNX Runtime
4. **Phase 4 (Tasks 16-17)**: 批量处理和核心功能完善
5. **Phase 5 (Tasks 18)**: 可选OCR功能
6. **Phase 6 (Tasks 19-24)**: CLI完善、文档、测试和发布准备

每个阶段都有Checkpoint任务，确保增量验证和用户反馈。

## 关键实现决策

### BBDown统一策略

本项目采用BBDown作为唯一的下载工具，简化架构和依赖：

**字幕下载**：
```bash
BBDown <url> --sub-only [--cookie <cookie_file>]
```
- 仅下载字幕文件，不下载视频
- 支持Cookie认证访问大会员内容
- 字幕不存在时会明确提示

**视频下载**（字幕不存在时）：
```bash
BBDown <url> [-q <quality>] [-mt] [--cookie <cookie_file>]
```
- 下载完整视频用于ASR识别
- 支持质量选择（-q 80表示1080P）
- 支持多线程下载加速

**优势**：
- 统一工具，减少依赖复杂度
- BBDown专为B站优化，稳定性好
- 支持最新的B站API和格式
- 无需维护多个下载工具的适配代码

**处理流程**：
```
URL验证 → BBDown --sub-only → 字幕解析 → 输出
                ↓ (无字幕)
         BBDown完整下载 → 音频提取 → ASR → 输出
```

### 依赖说明

**外部工具（需要单独安装）**：
- BBDown：B站视频下载（必需）
- FFmpeg：音频提取（必需）

**Python依赖**：
- 核心：ffmpeg-python
- ASR（可选）：funasr、openai-whisper
- OCR（可选）：paddleocr

**移除的依赖**：
- you-get：不再需要
- yt-dlp：不再需要
