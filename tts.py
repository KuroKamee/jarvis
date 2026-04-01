"""
Text-to-Speech using Fish Audio API with the MCU JARVIS voice.
"""

import httpx
import os
from dotenv import load_dotenv

load_dotenv()

JARVIS_VOICE_ID = "612b878b113047d9a770c069c8b4fdfe"


class TextToSpeech:
    def __init__(self, voice_id: str = JARVIS_VOICE_ID):
        self.api_key = os.getenv("FISH_API_KEY")
        self.voice_id = voice_id
        self.base_url = "https://api.fish.audio/v1/tts"

        if not self.api_key:
            raise ValueError("FISH_API_KEY not set in .env")

        print(f"[TTS] Fish Audio ready (voice: {self.voice_id[:12]}...)")

    async def synthesize(self, text: str) -> bytes:
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    self.base_url,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "text": text,
                        "reference_id": self.voice_id,
                        "format": "mp3",
                    }
                )
                response.raise_for_status()
                return response.content
            except httpx.HTTPStatusError as e:
                print(f"[TTS] API error {e.response.status_code}: {e.response.text}")
                return b""
            except Exception as e:
                print(f"[TTS] Error: {e}")
                return b""
