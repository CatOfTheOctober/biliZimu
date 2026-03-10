# Product Overview

## Purpose

Bilibili Video Text Extractor - 一个智能的B站视频文本提取工具

从B站视频中提取文字内容，支持：
- 官方字幕提取（含AI字幕）
- ASR语音识别（FunASR/Whisper）
- 多格式输出（SRT/JSON/TXT/Markdown）

## Key Features

### 已实现功能 ✅
- **智能两阶段处理**: 优先使用B站API获取字幕，无字幕时自动使用ASR
- **AI字幕支持**: 自动获取B站AI生成的字幕
- **Cookie管理**: 自动检测BBDown Cookie，支持一键登录
- **WBI签名**: 实现B站WBI签名算法，支持API访问
- **BBDown集成**: 统一使用BBDown进行字幕和视频下载
- **双ASR引擎**: FunASR（中文优化）+ Whisper（多语言）
- **多格式输出**: SRT、JSON、TXT、Markdown
- **CPU优化**: 支持INT8量化和ONNX Runtime加速
- **批量处理**: 支持批量处理多个视频
- **完整日志**: 详细的处理日志和错误追踪

### 开发中功能 🚧
- OCR硬字幕识别（实验性）
- 进度条优化
- Web界面

### 计划功能 📋
- Docker支持
- 更多输出格式
- 视频内容分析

## Target Users

- 内容创作者：需要提取视频字幕进行二次创作
- 学习者：需要提取教程视频的文字内容
- 研究人员：需要分析视频内容
- 开发者：需要批量处理B站视频

## Use Cases

1. **字幕提取**: 从有字幕的视频中提取文字
2. **语音识别**: 从无字幕的视频中识别语音
3. **批量处理**: 批量提取多个视频的文字内容
4. **格式转换**: 将字幕转换为不同格式
5. **内容分析**: 提取文字用于内容分析

## Project Status

- **Version**: 1.0.0
- **Status**: Beta
- **Test Coverage**: 79%
- **Tests**: 154 passing

## Documentation

- **README.md**: 项目说明和使用指南
- **docs/PROJECT_STRUCTURE.md**: 项目结构详细说明
- **docs/COOKIE_GUIDE.md**: Cookie使用指南
- **docs/AI_SUBTITLE_ANALYSIS.md**: AI字幕技术分析
- **.kiro/specs/**: 功能规范和设计文档

