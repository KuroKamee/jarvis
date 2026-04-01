"""
Speech-to-Text using faster-whisper with accuracy optimizations.
"""

import tempfile
import os
from faster_whisper import WhisperModel


class SpeechToText:
    def __init__(self, model_size: str = "base.en"):
        print(f"[STT] Loading whisper model '{model_size}'...")
        self.model = WhisperModel(model_size, device="cpu", compute_type="int8")
        print("[STT] Model loaded.")

    def transcribe(self, audio_bytes: bytes) -> str:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(audio_bytes)
            temp_path = f.name

        try:
            segments, info = self.model.transcribe(
                temp_path,
                beam_size=5,
                language="en",
                vad_filter=True,
                vad_parameters=dict(min_silence_duration_ms=500),
                initial_prompt="JARVIS, Hey JARVIS, shut down, goodbye, clipboard, remember, open, close, timer, volume, weather, screen, screenshot",
                temperature=0.0,
                condition_on_previous_text=True,
            )
            text = " ".join(seg.text for seg in segments).strip()
            return text
        except Exception as e:
            print(f"[STT] Transcription error: {e}")
            return ""
        finally:
            os.unlink(temp_path)
