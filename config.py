"""
config.py
---------
All the constants and settings for the app live here, so nothing is
hard-coded deep inside the other files. If Groq deprecates a model,
this is the only place you need to change it.
"""

import os
from dotenv import load_dotenv

load_dotenv()  # reads the .env file into environment variables

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

# ---- Models (check https://console.groq.com/docs/models if any of
#      these ever get deprecated - swap the string, nothing else changes) ----
CHAT_MODEL = "openai/gpt-oss-20b"                 # reasoning / teaching brain
STT_MODEL = "whisper-large-v3-turbo"              # speech -> text
TTS_MODEL = "canopylabs/orpheus-v1-english"       # text -> speech (playai-tts was decommissioned)
TTS_VOICE = "troy"                                # valid Orpheus voices: autumn, diana, hannah, austin, daniel, troy

# ---- Teaching / adaptation thresholds ----
RETEACH_THRESHOLD = 40    # score below this -> re-explain more simply
REINFORCE_THRESHOLD = 75  # score below this (but above RETEACH) -> practice more
# score >= REINFORCE_THRESHOLD -> move ahead

MIN_LEVEL = 1   # simplest explanation style
MAX_LEVEL = 3   # most advanced explanation style

# ---- Storage ----
DATA_DIR = "data"
PROGRESS_FILE = os.path.join(DATA_DIR, "progress.json")