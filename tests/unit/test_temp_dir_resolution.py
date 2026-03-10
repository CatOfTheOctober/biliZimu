"""测试临时目录路径解析功能。"""

import pytest
from pathlib import Path
from src.bilibili_extractor.core.config import Config


class TestTempDirResolution:
    """测试临时目录路径解析。"""
    
    def test_resolved_temp_dir_property(self):
        """测试 resolved_temp_dir 属性是否正确解析路径。"""
        config = Config()
        
        # 检查原始值
        assert config.temp_dir == "./temp"
        
        # 检查解析后的值
        resolved_path = config.resolved_temp_dir
        assert isinstance(resolved_path, Path)
        assert resolved_path.is_absolute()
        
        # 检查路径是否正确（相对于项目根目录）
        # 注意：这里我们只检查路径类型和格式，不检查具体值
        # 因为具体值取决于项目根目录的位置
        
    def test_resolved_temp_dir_with_custom_path(self):
        """测试使用自定义路径时的解析。"""
        # 测试绝对路径（Windows 风格）
        import os
        if os.name == 'nt':  # Windows
            abs_path = "C:\\temp\\custom"
        else:  # Unix/Linux
            abs_path = "/tmp/custom"
            
        config = Config(temp_dir=abs_path)
        assert config.temp_dir == abs_path
        assert config.resolved_temp_dir == Path(abs_path)
        
        # 测试相对路径
        config2 = Config(temp_dir="custom_temp")
        assert config2.temp_dir == "custom_temp"
        resolved_path = config2.resolved_temp_dir
        assert isinstance(resolved_path, Path)
        assert resolved_path.is_absolute()
        
    def test_resolved_output_dir_property(self):
        """测试 resolved_output_dir 属性是否正确解析路径。"""
        config = Config()
        
        # 检查原始值
        assert config.output_dir == "./output"
        
        # 检查解析后的值
        resolved_path = config.resolved_output_dir
        assert isinstance(resolved_path, Path)
        assert resolved_path.is_absolute()
        
    def test_path_resolution_consistency(self):
        """测试路径解析的一致性。"""
        config = Config()
        
        # 使用 resolve_path 方法应该得到相同的结果
        manual_resolution = config.resolve_path(config.temp_dir)
        property_resolution = config.resolved_temp_dir
        
        assert manual_resolution == property_resolution
        
    def test_temp_dir_creation(self):
        """测试临时目录可以被创建。"""
        config = Config()
        temp_dir = config.resolved_temp_dir
        
        # 确保目录可以被创建
        temp_dir.mkdir(parents=True, exist_ok=True)
        assert temp_dir.exists()
        assert temp_dir.is_dir()
        
        # 清理（可选）
        # 注意：在实际测试中，我们通常使用临时目录
        # 这里只是为了演示功能
        
    def test_config_loader_preserves_resolution(self):
        """测试 ConfigLoader 加载的配置也能正确解析路径。"""
        from src.bilibili_extractor.core.config import ConfigLoader
        import tempfile
        import yaml
        
        # 创建测试配置文件
        yaml_content = """
temp_dir: "./test_temp"
output_dir: "./test_output"
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            config_path = Path(f.name)
        
        try:
            config = ConfigLoader.load_from_file(config_path)
            
            # 检查原始值
            assert config.temp_dir == "./test_temp"
            assert config.output_dir == "./test_output"
            
            # 检查解析后的值
            assert isinstance(config.resolved_temp_dir, Path)
            assert config.resolved_temp_dir.is_absolute()
            
            assert isinstance(config.resolved_output_dir, Path)
            assert config.resolved_output_dir.is_absolute()
            
        finally:
            config_path.unlink()