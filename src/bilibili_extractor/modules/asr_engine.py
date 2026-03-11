"""ASR (Automatic Speech Recognition) engines."""

from abc import ABC, abstractmethod
from typing import List, Optional, Callable
from pathlib import Path
from bilibili_extractor.core.models import TextSegment


class ASRError(Exception):
    """Exception raised when ASR processing fails."""
    pass


class ASREngine(ABC):
    """Abstract base class for ASR engines.
    
    Validates: Requirement 5.1
    """

    @abstractmethod
    def transcribe(
        self, audio_path: Path, progress_callback: Optional[Callable] = None
    ) -> List[TextSegment]:
        """Transcribe audio to text.

        Args:
            audio_path: Path to audio file
            progress_callback: Optional callback for progress updates (receives percentage: float)

        Returns:
            List of TextSegment objects with timestamps

        Raises:
            ASRError: If transcription fails
            FileNotFoundError: If audio file doesn't exist or ASR library not installed
        """
        pass


class FunASREngine(ASREngine):
    """FunASR engine for Chinese speech recognition.
    
    Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.7, 5.8
    """

    def __init__(self, model: str = "paraformer-zh", model_path: Optional[str] = None, use_int8: bool = False, use_onnx: bool = False):
        """Initialize FunASR engine.

        Args:
            model: Model name to use (default: paraformer-zh)
            model_path: Path to local FunASR model directory
            use_int8: Whether to use INT8 quantization for CPU optimization
            use_onnx: Whether to use ONNX Runtime for acceleration
        """
        self.model = model
        self.model_path = model_path
        self.vad_model = "fsmn-vad"
        self.punc_model = "ct-punc"
        self.use_int8 = use_int8
        self.use_onnx = use_onnx
        self._pipeline = None

    def transcribe(
        self, audio_path: Path, progress_callback: Optional[Callable] = None
    ) -> List[TextSegment]:
        """Transcribe audio using FunASR.

        Args:
            audio_path: Path to audio file
            progress_callback: Optional callback for progress updates

        Returns:
            List of TextSegment objects with timestamps

        Raises:
            ASRError: If transcription fails
            FileNotFoundError: If audio file doesn't exist or FunASR not installed
        """
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        try:
            # Import FunASR (lazy import to avoid dependency issues)
            try:
                from funasr import AutoModel
            except ImportError as e:
                raise FileNotFoundError(
                    f"FunASR not installed or missing dependencies: {str(e)}. Please install it with: pip install funasr"
                )
            
            # Initialize pipeline if not already done (Requirement 5.2)
            if self._pipeline is None:
                if progress_callback:
                    progress_callback(5.0)  # Model loading progress
                
                # Configure model based on optimization settings
                model_name = self.model
                vad_name = self.vad_model
                punc_name = self.punc_model
                
                # 如果指定了模型路径，尝试从本地加载模型
                if self.model_path:
                    model_path = Path(self.model_path)
                    if model_path.exists():
                        # 查找具体模型子目录 (适配 ModelScope 下载结构)
                        # 结构: D:/Funasr_model/speech_seaco_paraformer_large_asr_nat-zh-cn-16k-common-vocab8404-pytorch/model.pt
                        for sub_dir in model_path.iterdir():
                            if sub_dir.is_dir():
                                if "paraformer" in sub_dir.name and "speech" in sub_dir.name:
                                    model_name = str(sub_dir)
                                elif "fsmn_vad" in sub_dir.name:
                                    vad_name = str(sub_dir)
                                elif "punc" in sub_dir.name:
                                    punc_name = str(sub_dir)

                if self.use_onnx and not self.model_path:
                    model_name = f"{self.model}-onnx"
                
                # Create pipeline with VAD and punctuation (Requirements 5.3, 5.4)
                self._pipeline = AutoModel(
                    model=model_name,
                    vad_model=vad_name,
                    punc_model=punc_name,
                    device="cpu",
                    quantize=self.use_int8,  # INT8 quantization if enabled
                    disable_update=True  # 禁用自动更新以提高启动速度
                )
                
                if progress_callback:
                    progress_callback(10.0)  # Model loaded
            
            # Transcribe audio (Requirement 5.7)
            if progress_callback:
                progress_callback(15.0)  # Starting transcription
            
            result = self._pipeline.generate(
                input=str(audio_path),
                batch_size_s=300,  # Process in 300-second batches
                hotword="",
            )
            
            if progress_callback:
                progress_callback(90.0)  # Transcription complete
            
            # Parse results into TextSegment objects (Requirement 5.8)
            segments = self._parse_funasr_result(result)
            
            if progress_callback:
                progress_callback(100.0)  # Done
            
            return segments
            
        except FileNotFoundError:
            raise
        except Exception as e:
            raise ASRError(f"FunASR transcription failed: {str(e)}")

    def _parse_funasr_result(self, result) -> List[TextSegment]:
        """Parse FunASR result into TextSegment objects.

        Args:
            result: FunASR result object

        Returns:
            List of TextSegment objects
        """
        segments = []
        
        # FunASR returns results in different formats depending on the model
        # Handle both list and dict formats
        if isinstance(result, list) and len(result) > 0:
            result_data = result[0]
        else:
            result_data = result
        
        # Extract text and timestamps
        if isinstance(result_data, dict):
            text = result_data.get("text", "")
            timestamps = result_data.get("timestamp", [])
            sentence_info = result_data.get("sentence_info", [])
            
            # 优先处理 sentence_info (FunASR 1.3.x 开启 VAD 后的标准返回格式)
            if sentence_info and isinstance(sentence_info, list):
                for sent in sentence_info:
                    start_time = float(sent.get("start", 0)) / 1000.0
                    end_time = float(sent.get("end", 0)) / 1000.0
                    sentence_text = sent.get("sentence", "").strip()
                    
                    if sentence_text:
                        segments.append(TextSegment(
                            start_time=start_time,
                            end_time=end_time,
                            text=sentence_text,
                            confidence=1.0,
                            source="asr"
                        ))
            
            # 如果没有 sentence_info，尝试原有的 timestamps (词级或旧版格式)
            elif timestamps and isinstance(timestamps, list) and not segments:
                for ts_item in timestamps:
                    if isinstance(ts_item, (list, tuple)) and len(ts_item) >= 3:
                        # Format: [word, start_ms, end_ms]
                        word = ts_item[0]
                        start_time = float(ts_item[1]) / 1000.0  # Convert ms to seconds
                        end_time = float(ts_item[2]) / 1000.0
                        
                        segments.append(TextSegment(
                            start_time=start_time,
                            end_time=end_time,
                            text=word,
                            confidence=1.0,  # FunASR doesn't provide confidence scores
                            source="asr"
                        ))
            
            # 最后的保底兜底逻辑
            if not segments and text:
                segments.append(TextSegment(
                    start_time=0.0,
                    end_time=0.0,
                    text=text,
                    confidence=1.0,
                    source="asr"
                ))
        
        # Sort by start_time to ensure monotonic order (Requirement 5.3)
        segments.sort(key=lambda s: s.start_time)
        
        return segments


class WhisperEngine(ASREngine):
    """Whisper engine for multilingual speech recognition.
    
    Validates: Requirements 5.5, 5.6, 5.7, 5.8
    """

    def __init__(self, model: str = "base", language: Optional[str] = None):
        """Initialize Whisper engine.

        Args:
            model: Model size (tiny/base/small/medium/large)
            language: Language code (optional, auto-detect if None)
        """
        self.model = model
        self.language = language
        self._model = None

    def transcribe(
        self, audio_path: Path, progress_callback: Optional[Callable] = None
    ) -> List[TextSegment]:
        """Transcribe audio using Whisper.

        Args:
            audio_path: Path to audio file
            progress_callback: Optional callback for progress updates

        Returns:
            List of TextSegment objects with timestamps

        Raises:
            ASRError: If transcription fails
            FileNotFoundError: If audio file doesn't exist or Whisper not installed
        """
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        try:
            # Import Whisper (lazy import to avoid dependency issues)
            try:
                import whisper
            except ImportError:
                raise FileNotFoundError(
                    "Whisper not installed. Please install it with: pip install openai-whisper"
                )
            
            # Load model if not already done (Requirement 5.6)
            if self._model is None:
                if progress_callback:
                    progress_callback(5.0)  # Model loading progress
                
                self._model = whisper.load_model(self.model, device="cpu")
                
                if progress_callback:
                    progress_callback(10.0)  # Model loaded
            
            # Transcribe audio (Requirement 5.7)
            if progress_callback:
                progress_callback(15.0)  # Starting transcription
            
            # Configure transcription options
            options = {
                "fp16": False,  # Use FP32 for CPU
                "verbose": False,
            }
            
            if self.language:
                options["language"] = self.language
            
            result = self._model.transcribe(str(audio_path), **options)
            
            if progress_callback:
                progress_callback(90.0)  # Transcription complete
            
            # Parse results into TextSegment objects (Requirement 5.8)
            segments = self._parse_whisper_result(result)
            
            if progress_callback:
                progress_callback(100.0)  # Done
            
            return segments
            
        except FileNotFoundError:
            raise
        except Exception as e:
            raise ASRError(f"Whisper transcription failed: {str(e)}")

    def _parse_whisper_result(self, result: dict) -> List[TextSegment]:
        """Parse Whisper result into TextSegment objects.

        Args:
            result: Whisper result dictionary

        Returns:
            List of TextSegment objects
        """
        segments = []
        
        # Whisper returns segments with timestamps
        for segment in result.get("segments", []):
            text = segment.get("text", "").strip()
            start_time = float(segment.get("start", 0.0))
            end_time = float(segment.get("end", 0.0))
            
            if text:
                segments.append(TextSegment(
                    start_time=start_time,
                    end_time=end_time,
                    text=text,
                    confidence=1.0,  # Whisper doesn't provide segment-level confidence
                    source="asr"
                ))
        
        # Sort by start_time to ensure monotonic order
        segments.sort(key=lambda s: s.start_time)
        
        return segments

