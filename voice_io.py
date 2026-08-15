"""
voice_io.py
-----------
Thin wrappers around Groq's speech endpoints:
  - transcribe(): student's spoken audio (from st.audio_input) -> text
  - synthesize(): tutor's text -> spoken audio bytes (wav), for st.audio

synthesize() never raises on a rate limit or any API error - it returns
empty bytes so the app can fall back to text-only instead of crashing
mid-demo. Orpheus's free tier has a small daily token quota, so this
matters in practice, not just in theory.
"""

import groq
from groq import Groq
from config import GROQ_API_KEY, STT_MODEL, TTS_MODEL, TTS_VOICE

_client = Groq(api_key=GROQ_API_KEY)


def transcribe(audio_file) -> str:
    """
    audio_file: the object returned by st.audio_input (a file-like
    object with .wav bytes) OR any file-like object opened in 'rb' mode.
    Returns the transcribed text (empty string if nothing was said or
    if the API call fails).
    """
    if audio_file is None:
        return ""

    try:
        audio_file.seek(0)
    except Exception:
        pass

    try:
        transcription = _client.audio.transcriptions.create(
            file=("answer.wav", audio_file.read()),
            model=STT_MODEL,
            language="en",
            temperature=0.0,
        )
        return (transcription.text or "").strip()
    except groq.RateLimitError:
        return ""
    except Exception:
        return ""


def synthesize(text: str) -> bytes:
    """
    Converts text to speech and returns raw WAV audio bytes, ready to
    hand to st.audio(audio_bytes, format="audio/wav", autoplay=True).

    Returns b"" (instead of raising) on a rate limit or any other API
    error, so the caller can gracefully fall back to text-only.
    """
    if not text:
        return b""

    # Orpheus works best on plain, moderately short text - trim
    # anything extreme so a very long explanation doesn't fail the call.
    text = text[:4000]

    try:
        response = _client.audio.speech.create(
            model=TTS_MODEL,
            voice=TTS_VOICE,
            input=text,
            response_format="wav",
        )
        return response.content
    except groq.RateLimitError:
        return b""
    except Exception:
        return b""