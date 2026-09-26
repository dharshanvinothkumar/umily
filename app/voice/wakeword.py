"""
Umily — Wake Word Detector

Real-time microphone stream wake-word detection using sounddevice and STTEngine.
Monitors soundcard microphone input for trigger phrases like "Hey Umily" or "Umily".
"""

import io
import wave
import threading
import time
import numpy as np
from typing import Callable, Optional
from loguru import logger

from app.voice.stt import STTEngine


class WakeWordDetector:
    """Wake word detection service reading real-time microphone stream."""

    def __init__(self, wake_words: Optional[list[str]] = None, sample_rate: int = 16000):
        self.wake_words = wake_words or [
            "wake bro", "hey bro", "hey umily", "umily", "hey family", "family", "hey emily", "emily", "hey humily", "humily"
        ]
        self.sample_rate = sample_rate


        self.stt = STTEngine()
        self._is_listening = False
        self._thread: Optional[threading.Thread] = None
        self._callback: Optional[Callable[[], None]] = None
        self._lock = threading.Lock()

    def start_listening(self, on_wake: Callable[[], None]):
        """Start listening for wake word in background thread (idempotent)."""
        with self._lock:
            if self._is_listening and self._thread and self._thread.is_alive():
                logger.warning("Wake word detector is already running.")
                return

            self._callback = on_wake
            self._is_listening = True
            self._thread = threading.Thread(target=self._listen_loop, daemon=True)
            self._thread.start()
            logger.info(f"Real-time Wake Word Detector started for triggers: {self.wake_words}")

    def stop_listening(self):
        """Stop wake word listener cleanly."""
        with self._lock:
            self._is_listening = False
        if self._thread and self._thread.is_alive() and threading.current_thread() != self._thread:
            self._thread.join(timeout=1.5)
        logger.info("Wake word detector stopped.")


    def is_wake_word(self, text: str) -> bool:
        """Check if input text contains any configured wake word."""
        text_lower = text.lower()
        return any(word in text_lower for word in self.wake_words)

    @property
    def is_active(self) -> bool:
        return self._is_listening

    def record_microphone_audio(self, duration_sec: float = 3.0) -> bytes:
        """Record audio bytes directly from microphone for given duration."""
        try:
            import sounddevice as sd
            num_samples = int(self.sample_rate * duration_sec)
            audio_data = sd.rec(num_samples, samplerate=self.sample_rate, channels=1, dtype="int16")
            sd.wait()
            return self._numpy_to_wav(audio_data.flatten())
        except Exception as e:
            logger.error(f"Error recording microphone audio: {e}")
            return b""

    def _numpy_to_wav(self, pcm_data: np.ndarray) -> bytes:
        """Convert int16 PCM numpy array to WAV bytes."""
        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(self.sample_rate)
            wav_file.writeframes(pcm_data.tobytes())
        return buffer.getvalue()

    def _listen_loop(self):
        """Main background loop monitoring microphone energy and transcribing speech."""
        try:
            import sounddevice as sd
        except ImportError:
            logger.warning("sounddevice not available. WakeWordDetector running in polling mode.")
            while self._is_listening:
                time.sleep(1.0)
            return

        buffer = []
        is_speech_active = False
        silence_count = 0
        speech_threshold = 500  # PCM amplitude threshold for speech detection

        def audio_callback(indata, frames, time_info, status):
            nonlocal is_speech_active, silence_count
            if not self._is_listening:
                return

            pcm = indata.copy().flatten()
            amplitude = np.max(np.abs(pcm))

            if amplitude > speech_threshold:
                buffer.extend(pcm)
                is_speech_active = True
                silence_count = 0
            elif is_speech_active:
                buffer.extend(pcm)
                silence_count += 1
                # If ~1.2s silence after speech, process buffer
                if silence_count > 15:
                    audio_arr = np.array(buffer, dtype=np.int16)
                    buffer.clear()
                    is_speech_active = False
                    silence_count = 0

                    if len(audio_arr) > self.sample_rate * 0.8: # At least 0.8s of audio
                        wav_bytes = self._numpy_to_wav(audio_arr)
                        text = self.stt.transcribe_bytes(wav_bytes)
                        logger.info(f"[Mic Audio Stream] Heard text: {text!r}")

                        if self.is_wake_word(text) and self._callback:
                            logger.info("Wake word detected! Invoking wake callback.")
                            self._callback()

        try:
            with sd.InputStream(
                samplerate=self.sample_rate,
                channels=1,
                dtype="int16",
                callback=audio_callback,
                blocksize=1600
            ):
                while self._is_listening:
                    time.sleep(0.2)
        except Exception as e:
            logger.error(f"Error in microphone input stream loop: {e}")
            while self._is_listening:
                time.sleep(1.0)
