# Project Structure

## Current Organization

```
D:\Kiro_proj\Test1/
├── .kiro/              # Kiro AI assistant files (specs, steering)
├── src/                # Project source code
├── tests/              # Test suite
├── config/             # Configuration files
├── tools/              # External tools (BBDown, FFmpeg)
├── docs/               # Documentation
├── output/             # Output directory (default)
└── temp/               # Temporary files
```

## Conventions

### File Organization

- `.kiro/`: Kiro AI specifications and steering rules (managed by Kiro)
- `src/bilibili_extractor/`: All Python source code, organized by modules
- `tests/`: Unit, integration, and property tests
- `config/`: YAML configuration files (example_config.yaml is the template)
- `tools/`: External dependencies (BBDown.exe, FFmpeg)
- `docs/`: Project documentation and analysis reports
- `output/`: Default output directory for extracted subtitles
- `temp/`: Temporary files during processing

### Code Organization

- `src/bilibili_extractor/core/`: Core business logic (config, extractor, models)
- `src/bilibili_extractor/modules/`: Feature modules (auth, API, parsers, etc.)
- `src/bilibili_extractor/utils/`: Utility functions (logger, validators, etc.)
- Separate concerns appropriately (business logic, data access, presentation)
- Keep modules focused and cohesive

### Configuration Management

- `config/example_config.yaml`: Template configuration (committed to Git)
- `config/config.yaml`: User configuration (ignored by Git)
- `config/default_config.yaml`: Default values
- Priority: CLI args > config file > default values

### External Tools

- `tools/BBDown/`: BBDown executable and cookie file
- `tools/ffmpeg/`: FFmpeg binaries
- System automatically detects tools in this directory
- Alternative: Add tools to system PATH

## Directory Details

See `docs/PROJECT_STRUCTURE.md` for detailed documentation on:
- Directory purposes and contents
- File search priorities
- Best practices
- Maintenance commands

