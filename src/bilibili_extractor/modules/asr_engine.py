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

    def __init__(self, model: str = "paraformer-zh", use_int8: bool = False, use_onnx: bool = False):
        """Initialize FunASR engine.

        Args:
            model: Model name to use (default: paraformer-zh)
            use_int8: Whether to use INT8 quantization for CPU optimization
            use_onnx: Whether to use ONNX Runtime for acceleration
        """
        self.model = model
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
            except ImportError:
                raise FileNotFoundError(
                    "FunASR not installed. Please install it with: pip install funasr"
                )
            
            # Initialize pipeline if not already done (Requirement 5.2)
            if self._pipeline is None:
                if progress_callback:
                    progress_callback(5.0)  # Model loading progress
                
                # Configure model based on optimization settings
                model_name = self.model
                if self.use_onnx:
                    model_name = f"{self.model}-onnx"
                
                # Create pipeline with VAD and punctuation (Requirements 5.3, 5.4)
                self._pipeline = AutoModel(
                    model=model_name,
                    vad_model=self.vad_model,
                    punc_model=self.punc_model,
                    device="cpu",
                    quantize=self.use_int8  # INT8 quantization if enabled
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
            
            # If we have word-level timestamps (Requirement 5.3)
            if timestamps and isinstance(timestamps, list):
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
            else:
                # No timestamps, create single segment with full text
                if text:
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

