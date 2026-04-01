"""
LLM backend with mood awareness, vision, smart clipboard rewrite.
"""

import os
import anthropic
from dotenv import load_dotenv

load_dotenv()

SYSTEM_PROMPT = """You are JARVIS — Just A Rather Very Intelligent System.

VOICE: British, refined, dry wit. Paul Bettany's JARVIS. "Sir" sparingly.
{mood_hint}

FORMAT (spoken via TTS): 1-2 sentences. 3 max. No bullets, lists, markdown, asterisks. Numbers as words.

ACTIONS — include tags (stripped before speaking):

Apps: [ACTION:OPEN app] [ACTION:CLOSE app]
Volume: [ACTION:VOLUME_UP] [ACTION:VOLUME_DOWN] [ACTION:MUTE] [ACTION:UNMUTE]

Spotify: [ACTION:SPOTIFY_PLAY query] [ACTION:SPOTIFY_PAUSE] [ACTION:SPOTIFY_NEXT] [ACTION:SPOTIFY_PREV]
[ACTION:SPOTIFY_CURRENT] [ACTION:SPOTIFY_SHUFFLE] [ACTION:SPOTIFY_REPEAT] [ACTION:SPOTIFY_VOLUME 0-100]

Timers: [ACTION:TIMER seconds name] [ACTION:TIMER_CHECK] [ACTION:TIMER_CANCEL name]
Search: [ACTION:SEARCH query]  Weather: [ACTION:WEATHER location]
Screen: [ACTION:SCREENSHOT]

Focus: [ACTION:FOCUS minutes] [ACTION:FOCUS_END] [ACTION:FOCUS_STATUS]
Notes: [ACTION:NOTE content] [ACTION:NOTES_READ] [ACTION:NOTES_SEARCH query] [ACTION:NOTES_CLEAR]
System: [ACTION:SYSTEM_STATUS]
Clipboard: [ACTION:READ_CLIPBOARD]
Smart Rewrite: [ACTION:REWRITE_CLIPBOARD style] — rewrite clipboard text in given style (professional, casual, shorter, etc)

Math: [ACTION:MATH expression]  Convert: [ACTION:CONVERT value from to]  Countdown: [ACTION:TIME_UNTIL time]
Files: [ACTION:FIND_FILE query] — search Downloads/Documents/Desktop
Briefing: [ACTION:BRIEFING] — daily summary
Trivia: [ACTION:TRIVIA category] — quiz (history, science, general, tech)

Random: [ACTION:COIN_FLIP] [ACTION:ROLL_DICE sides] [ACTION:RANDOM_NUMBER low high]
Memory: [REMEMBER key=value]

BUILT-IN (no tags): translations, definitions, jokes, general knowledge, conversation, roasts.
For "roast me": give a witty, dry British roast. Clever, not mean.
For jokes: dry, sophisticated humor in character.

RULES: Always include spoken response + tag. Be specific with Spotify (include artist).
For math: [ACTION:MATH 347 * 0.20]. For convert: [ACTION:CONVERT 180 cm feet].
Timer seconds: 5 min = 300. Weather default: "auto".

NEVER: "as an AI", formatting, "Certainly!", "Of course!", "Great question!"
"""


class LLM:
    def __init__(self):
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key: raise ValueError("ANTHROPIC_API_KEY not set")
        self.client = anthropic.AsyncAnthropic(api_key=api_key)
        self.conversation_history: list[dict] = []
        self.user_name = os.getenv("USER_NAME", "sir")
        print(f"[LLM] Haiku ready. User: {self.user_name}")

    def _build_system(self, mood_hint: str = "") -> str:
        return SYSTEM_PROMPT.replace("sir", self.user_name).replace("{mood_hint}", mood_hint)

    async def chat(self, user_message: str, memory_context: str = "", mood_hint: str = "") -> str:
        content = f"[Context]\n{memory_context}\n\n[User]\n{user_message}" if memory_context else user_message
        self.conversation_history.append({"role": "user", "content": content})
        if len(self.conversation_history) > 60:
            self.conversation_history = self.conversation_history[-60:]
        try:
            response = await self.client.messages.create(
                model="claude-haiku-4-5-20251001", max_tokens=250,
                system=self._build_system(mood_hint),
                messages=self.conversation_history
            )
            reply = response.content[0].text
            self.conversation_history.append({"role": "assistant", "content": reply})
            return reply
        except anthropic.APIError as e:
            print(f"[LLM] {e}")
            return "Temporary malfunction. Do try again."

    async def chat_with_image(self, user_message: str, image_base64: str,
                               media_type: str = "image/jpeg", memory_context: str = "", mood_hint: str = "") -> str:
        content = []
        text = f"[Context]\n{memory_context}\n\n[User]\n{user_message}" if memory_context else user_message
        content.append({"type": "text", "text": text})
        content.append({"type": "image", "source": {"type": "base64", "media_type": media_type, "data": image_base64}})
        self.conversation_history.append({"role": "user", "content": content})
        if len(self.conversation_history) > 40:
            self.conversation_history = self.conversation_history[-40:]
        try:
            response = await self.client.messages.create(
                model="claude-haiku-4-5-20251001", max_tokens=400,
                system=self._build_system(mood_hint),
                messages=self.conversation_history
            )
            reply = response.content[0].text
            self.conversation_history.append({"role": "assistant", "content": reply})
            return reply
        except anthropic.APIError as e:
            print(f"[LLM] Vision: {e}")
            return "Couldn't analyze the screen."

    async def rewrite_text(self, text: str, style: str = "professional") -> str:
        """Rewrite text in a given style. Used for smart clipboard."""
        try:
            response = await self.client.messages.create(
                model="claude-haiku-4-5-20251001", max_tokens=500,
                system=f"Rewrite the following text to sound {style}. Return ONLY the rewritten text, nothing else.",
                messages=[{"role": "user", "content": text}]
            )
            return response.content[0].text
        except:
            return text

    def clear_history(self):
        self.conversation_history = []
