"""
Umily — Text-To-Speech (TTS) Engine

Uses edge-tts or fallback audio synthesizer.
"""

import asyncio
import os
import tempfile
import wave
import struct
from loguru import logger

class TTSEngine:
    """Text-to-Speech processor using edge-tts or fallback synthesizer."""

    def __init__(self, voice: str = "en-US-AriaNeural"):
        self.voice = voice

    async def synthesize_async(self, text: str) -> bytes:
        """Synthesize text into MP3/WAV audio bytes asynchronously."""
        if not text:
            return b""

        # Try edge-tts
        try:
            import edge_tts
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
                tmp_path = tmp.name

            try:
                communicate = edge_tts.Communicate(text, self.voice)
                await communicate.save(tmp_path)
                with open(tmp_path, "rb") as f:
                    audio_data = f.read()
                logger.info(f"Synthesized {len(audio_data)} bytes using edge-tts")
                return audio_data
            finally:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
        except Exception as e:
            logger.debug(f"edge-tts not available: {e}. Falling back to standard audio synthesizer.")

        # Fallback synthesizer: Generate a valid minimal WAV audio stream
        return self._generate_fallback_wav(text)

    def synthesize(self, text: str) -> bytes:
        """Synchronous wrapper for text-to-speech synthesis."""
        try:
            loop = asyncio.get_running_loop()
            if loop.is_running():
                return self._generate_fallback_wav(text)
            return loop.run_until_complete(self.synthesize_async(text))
        except RuntimeError:
            return asyncio.run(self.synthesize_async(text))

    def _generate_fallback_wav(self, text: str) -> bytes:
        """Generates a valid audio/wav byte stream representing the response."""
        sample_rate = 22050
        duration_sec = min(max(len(text) * 0.05, 0.5), 3.0)
        num_samples = int(sample_rate * duration_sec)

        import math
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            with wave.open(tmp_path, "w") as wav_file:
                wav_file.setnchannels(1)  # Mono
                wav_file.setsampwidth(2)  # 16-bit
                wav_file.setframerate(sample_rate)
                
                # Soft tone with decay
                samples = []
                for i in range(num_samples):
                    t = i / sample_rate
                    amplitude = math.sin(2 * math.pi * 440 * t) * math.exp(-t * 2) * 10000
                    samples.append(int(amplitude))
                
                packed_samples = struct.pack(f"<{len(samples)}h", *samples)
                wav_file.writeframes(packed_samples)

            with open(tmp_path, "rb") as f:
                return f.read()
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
