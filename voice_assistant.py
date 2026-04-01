"""
J.A.R.V.I.S. — Voice Assistant (Final)
Practical daily-use version. Cross-platform.

python3 voice_assistant.py
"""

import asyncio, io, json, math as mathlib, os, re, struct, sys, tempfile
import threading, time, warnings, wave, random
from datetime import datetime, timedelta

import numpy as np, httpx

warnings.filterwarnings("ignore", category=ResourceWarning)
warnings.filterwarnings("ignore", category=RuntimeWarning)

try: import pyaudio
except ImportError: print("pip3 install pyaudio"); sys.exit(1)

from openwakeword.model import Model as WakeModel
from stt import SpeechToText
from tts import TextToSpeech
from llm import LLM
from memory import Memory, extract_memories
from actions import (open_app, close_app, volume_up, volume_down, mute, unmute,
    set_timer, get_active_timers, cancel_timer, capture_screen, active_timers)
from spotify import (spotify_play, spotify_play_pause, spotify_next, spotify_previous,
    spotify_get_current, spotify_shuffle_on, spotify_repeat, spotify_set_volume)
from search import web_search, get_weather
from tools import (start_focus_mode, end_focus_mode, get_focus_status, get_system_status,
    add_note, get_recent_notes, clear_notes, search_notes, get_clipboard, set_clipboard,
    read_clipboard_aloud, coin_flip, roll_dice, random_number, evaluate_math,
    convert_units, time_until, find_file, get_daily_briefing, get_trivia,
    check_easter_egg, get_mood_context, focus_state)

# ── Load Settings ─────────────────────────────────────

def _load_settings():
    defaults = {
        "whisper_model": "base.en", "silence_seconds": 1.5,
        "conversation_timeout": 6, "interrupt_threshold": 2000,
        "energy_threshold": 300, "user_name": "sir",
        "personality": "default", "response_length": "short",
        "startup_greeting": True, "enable_spotify": True,
        "enable_focus_mode": True, "enable_screen_capture": True,
        "enable_file_finder": True, "enable_easter_eggs": True,
        "chime_volume": 0.25, "tts_voice_id": "612b878b113047d9a770c069c8b4fdfe",
    }
    if os.path.exists("jarvis_settings.json"):
        try:
            with open("jarvis_settings.json") as f:
                defaults.update(json.load(f))
        except: pass
    # .env overrides for name
    from dotenv import load_dotenv; load_dotenv()
    env_name = os.getenv("USER_NAME")
    if env_name and defaults["user_name"] == "sir":
        defaults["user_name"] = env_name
    return defaults

SETTINGS = _load_settings()

RATE = 16000; CHANNELS = 1; CHUNK = 1024; FORMAT = pyaudio.paInt16
COMMAND_SILENCE_SECONDS = SETTINGS["silence_seconds"]
COMMAND_MAX_SECONDS = 15
CONVERSATION_TIMEOUT = SETTINGS["conversation_timeout"]
INTERRUPT_ENERGY_THRESHOLD = SETTINGS["interrupt_threshold"]
ENERGY_THRESHOLD = SETTINGS["energy_threshold"]
WHISPER_MODEL = SETTINGS["whisper_model"]
CHIME_VOL = SETTINGS["chime_volume"]

# ── Conversation Log ──────────────────────────────────
LOG_FILE = "jarvis_log.json"

def _log_interaction(user_text: str, jarvis_text: str):
    try:
        log = []
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE) as f: log = json.load(f)
        log.append({
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "user": user_text,
            "jarvis": jarvis_text
        })
        # Keep last 500 interactions
        log = log[-500:]
        with open(LOG_FILE, 'w') as f: json.dump(log, f, indent=2)
    except: pass

# ── Fast-Path Commands ────────────────────────────────
# These bypass the LLM for instant response

def _check_fast_path(text: str) -> str | None:
    """Check if this is a simple command we can answer instantly."""
    t = text.lower().strip()

    # Time
    if t in ["what time is it", "what's the time", "time", "what time"]:
        return f"It's {datetime.now().strftime('%I:%M %p')}."

    # Date
    if t in ["what's the date", "what day is it", "what's today", "date", "today"]:
        return datetime.now().strftime("It's %A, %B %d, %Y.")

    # Help
    if t in ["what can you do", "help", "commands", "what are your commands"]:
        return ("I can play music, set timers, search the web, check the weather, "
                "take notes, do math, convert units, control apps and volume, "
                "analyze your screen, manage focus mode, find files, and much more. "
                "Just ask naturally.")

    # Quick math (simple patterns)
    simple_math = re.match(r'^(?:what\'?s?\s+)?(\d+)\s*[\+\-\*x×/÷]\s*(\d+)\s*\??$', t)
    if simple_math:
        try:
            expr = t.replace("what's", "").replace("what is", "").replace("?", "").strip()
            expr = expr.replace("x", "*").replace("×", "*").replace("÷", "/")
            result = eval(expr)
            if isinstance(result, float) and result == int(result):
                result = int(result)
            return f"That's {result}."
        except: pass

    return None

# ── Help Text ─────────────────────────────────────────

QUICK_ACKS = ["On it.", "One moment.", "Working on that.", "Right away.",
              "Let me check.", "Looking into it."]


class VoiceAssistant:
    def __init__(self):
        print("=" * 50)
        print("  J.A.R.V.I.S. — Voice Assistant")
        print("=" * 50)

        self.stt = SpeechToText(model_size=WHISPER_MODEL)
        self.tts = TextToSpeech()
        self.llm = LLM()
        self.memory = Memory()
        self.audio = pyaudio.PyAudio()
        self.is_speaking = False
        self.interrupted = False
        self.should_shutdown = False
        self.quiet_mode = False
        self.start_time = time.time()
        self.commands_processed = 0
        self.last_response = ""
        self._last_battery_warning = 0

        self._chime = self._tone([880, 1320], 0.12, CHIME_VOL)
        self._shutdown_chime = self._tone([1320, 660], 0.2, CHIME_VOL)
        self._think_chime = self._tone([1100], 0.08, CHIME_VOL * 0.6)
        self._timer_alarm = self._tone([880, 1100, 880, 1100], 0.2, CHIME_VOL * 1.4)
        self._focus_chime = self._tone([660, 880, 1100], 0.15, CHIME_VOL * 1.2)
        self._error_chime = self._tone([440, 330], 0.15, CHIME_VOL * 0.8)

        print(f"  Model: {WHISPER_MODEL}")
        print(f"  User: {SETTINGS['user_name']}")
        print(f"  Personality: {SETTINGS['personality']}")
        print("=" * 50)
        print("  All systems online.")
        print('  Say "Hey JARVIS" to activate.')
        print("=" * 50)

    # ── Sounds ────────────────────────────────────────

    def _tone(self, freqs, dur=0.15, vol=0.3, sr=44100):
        parts = []
        for f in freqs:
            frames = []
            for i in range(int(sr * dur)):
                t = i / sr
                env = min(t / 0.02, 1.0) * min((dur - t) / 0.02, 1.0)
                frames.append(struct.pack('h', int(env * vol * mathlib.sin(2 * mathlib.pi * f * t) * 32767)))
            parts.append(b''.join(frames))
        gap = b'\x00\x00' * int(sr * 0.03)
        buf = io.BytesIO()
        with wave.open(buf, 'wb') as wf:
            wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(sr)
            wf.writeframes(gap.join(parts))
        return buf.getvalue()

    def _play_sound(self, data):
        try:
            buf = io.BytesIO(data)
            with wave.open(buf, 'rb') as wf:
                s = self.audio.open(format=self.audio.get_format_from_width(wf.getsampwidth()),
                    channels=wf.getnchannels(), rate=wf.getframerate(), output=True)
                d = wf.readframes(1024)
                while d: s.write(d); d = wf.readframes(1024)
                s.stop_stream(); s.close()
        except: pass

    def _timer_done(self, name):
        self._play_sound(self._timer_alarm); self._play_sound(self._timer_alarm)
        asyncio.run(self._speak(f"Your {name} timer has finished."))

    def _focus_done(self, name):
        self._play_sound(self._focus_chime); end_focus_mode()
        asyncio.run(self._speak("Focus session complete. Time for a break."))

    # ── Recording ─────────────────────────────────────

    def _record(self, max_sec=COMMAND_MAX_SECONDS, sil_sec=COMMAND_SILENCE_SECONDS):
        stream = self.audio.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)
        frames, silent = [], 0
        sil_thresh = int(RATE / CHUNK * sil_sec)
        print("[Mic] Listening...")

        # Auto-pause Spotify while recording
        if SETTINGS["enable_spotify"]:
            try:
                from spotify import spotify_get_current
                current = spotify_get_current()
                if "Now playing" in current:
                    self._spotify_was_playing = True
                    from spotify import spotify_play_pause
                    spotify_play_pause()
                else:
                    self._spotify_was_playing = False
            except:
                self._spotify_was_playing = False

        for i in range(int(RATE / CHUNK * max_sec)):
            data = stream.read(CHUNK, exception_on_overflow=False)
            frames.append(data)
            energy = sum(abs(x) for x in struct.unpack(f'{CHUNK}h', data)) / CHUNK
            silent = silent + 1 if energy < ENERGY_THRESHOLD else 0
            if silent >= sil_thresh and i > int(RATE / CHUNK * 1.5): break
        stream.stop_stream(); stream.close()
        print(f"[Mic] Got {len(frames) * CHUNK / RATE:.1f}s")
        return self._to_wav(frames)

    def _resume_spotify(self):
        """Resume Spotify if it was playing before we interrupted."""
        if getattr(self, '_spotify_was_playing', False) and SETTINGS["enable_spotify"]:
            try:
                from spotify import spotify_play_pause
                spotify_play_pause()
                self._spotify_was_playing = False
            except: pass

    def _followup(self, timeout=CONVERSATION_TIMEOUT):
        stream = self.audio.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)
        cps = RATE / CHUNK; max_w = int(cps * timeout)
        speech, frames, silent = False, [], 0
        sil_thresh = int(cps * COMMAND_SILENCE_SECONDS)
        print(f"[Conversation] Waiting ({timeout}s)...")
        for i in range(max_w + int(cps * COMMAND_MAX_SECONDS)):
            data = stream.read(CHUNK, exception_on_overflow=False)
            energy = sum(abs(x) for x in struct.unpack(f'{CHUNK}h', data)) / CHUNK
            if not speech:
                if energy > ENERGY_THRESHOLD: speech = True; frames.append(data)
                elif i >= max_w: stream.stop_stream(); stream.close(); return None
            else:
                frames.append(data)
                silent = silent + 1 if energy < ENERGY_THRESHOLD else 0
                if silent >= sil_thresh and len(frames) > int(cps * 0.5): break
        stream.stop_stream(); stream.close()
        return self._to_wav(frames) if frames else None

    def _to_wav(self, frames):
        buf = io.BytesIO()
        with wave.open(buf, 'wb') as wf:
            wf.setnchannels(CHANNELS); wf.setsampwidth(self.audio.get_sample_size(FORMAT))
            wf.setframerate(RATE); wf.writeframes(b''.join(frames))
        return buf.getvalue()

    # ── Audio ─────────────────────────────────────────

    def _monitor_interrupt(self):
        try:
            mic = self.audio.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)
            while self.is_speaking:
                try:
                    data = mic.read(CHUNK, exception_on_overflow=False)
                    energy = sum(abs(x) for x in struct.unpack(f'{CHUNK}h', data)) / CHUNK
                    if energy > INTERRUPT_ENERGY_THRESHOLD: self.interrupted = True; break
                except: break
            mic.stop_stream(); mic.close()
        except: pass

    def _play_audio(self, mp3):
        self.is_speaking = True; self.interrupted = False
        try:
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as f: f.write(mp3); mp3p = f.name
            wavp = mp3p.replace('.mp3', '.wav')
            os.system(f'ffmpeg -y -i {mp3p} -ar 44100 -ac 1 -acodec pcm_s16le {wavp} -loglevel quiet')
            if not os.path.exists(wavp): return
            mon = threading.Thread(target=self._monitor_interrupt, daemon=True); mon.start()
            with wave.open(wavp, 'rb') as wf:
                spk = self.audio.open(format=self.audio.get_format_from_width(wf.getsampwidth()),
                    channels=wf.getnchannels(), rate=wf.getframerate(), output=True)
                d = wf.readframes(CHUNK)
                while d:
                    if self.interrupted: break
                    spk.write(d); d = wf.readframes(CHUNK)
                spk.stop_stream(); spk.close()
            self.is_speaking = False; mon.join(timeout=1)
            try: os.unlink(mp3p)
            except: pass
            try: os.unlink(wavp)
            except: pass
        except Exception as e: print(f"[Audio] {e}")
        finally: self.is_speaking = False

    async def _speak(self, text):
        if not text: return
        if self.quiet_mode:
            print(f"[JARVIS] (quiet) {text}")
            return
        self.is_speaking = True
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                async with client.stream("POST", self.tts.base_url,
                    headers={"Authorization": f"Bearer {self.tts.api_key}", "Content-Type": "application/json"},
                    json={"text": text, "reference_id": self.tts.voice_id, "format": "mp3"}) as resp:
                    if resp.status_code != 200: print(f"[TTS] Error {resp.status_code}"); return
                    audio = b""
                    async for chunk in resp.aiter_bytes(4096): audio += chunk
                    if audio: self._play_audio(audio)
        except Exception as e: print(f"[TTS] {e}")
        finally: self.is_speaking = False

    async def _quick_ack(self):
        await self._speak(random.choice(QUICK_ACKS))

    # ── Battery Warning ───────────────────────────────

    def _check_battery(self):
        """Proactively warn about low battery."""
        if time.time() - self._last_battery_warning < 600:  # Max once per 10 min
            return
        try:
            import psutil
            bat = psutil.sensors_battery()
            if bat and not bat.power_plugged:
                if bat.percent <= 10:
                    self._last_battery_warning = time.time()
                    asyncio.run(self._speak(f"Battery is critically low at {int(bat.percent)} percent. You should plug in soon."))
                elif bat.percent <= 20:
                    self._last_battery_warning = time.time()
                    asyncio.run(self._speak(f"Battery at {int(bat.percent)} percent. Might want to find a charger."))
        except: pass

    # ── Actions ───────────────────────────────────────

    def _needs_quick_ack(self, text):
        return any(a in text for a in ['ACTION:SEARCH', 'ACTION:WEATHER', 'ACTION:SCREENSHOT',
            'ACTION:SPOTIFY_PLAY', 'ACTION:FIND_FILE', 'ACTION:BRIEFING', 'ACTION:REWRITE_CLIPBOARD'])

    async def _process_actions(self, text: str) -> str:
        # Apps
        for m in re.finditer(r'\[ACTION:OPEN\s+(.+?)\]', text): open_app(m.group(1).strip())
        for m in re.finditer(r'\[ACTION:CLOSE\s+(.+?)\]', text): close_app(m.group(1).strip())

        # Volume
        if '[ACTION:VOLUME_UP]' in text: volume_up()
        if '[ACTION:VOLUME_DOWN]' in text: volume_down()
        if '[ACTION:MUTE]' in text: mute()
        if '[ACTION:UNMUTE]' in text: unmute()

        # Spotify
        if SETTINGS["enable_spotify"]:
            for m in re.finditer(r'\[ACTION:SPOTIFY_PLAY\s+(.+?)\]', text): spotify_play(m.group(1).strip())
            if '[ACTION:SPOTIFY_PAUSE]' in text: spotify_play_pause()
            if '[ACTION:SPOTIFY_NEXT]' in text: spotify_next()
            if '[ACTION:SPOTIFY_PREV]' in text: spotify_previous()
            if '[ACTION:SPOTIFY_SHUFFLE]' in text: spotify_shuffle_on()
            if '[ACTION:SPOTIFY_REPEAT]' in text: spotify_repeat()
            for m in re.finditer(r'\[ACTION:SPOTIFY_VOLUME\s+(\d+)\]', text): spotify_set_volume(int(m.group(1)))

        spotify_info = ""
        if '[ACTION:SPOTIFY_CURRENT]' in text and SETTINGS["enable_spotify"]:
            spotify_info = spotify_get_current()

        # Timers
        for m in re.finditer(r'\[ACTION:TIMER\s+(\d+)\s*(.*?)\]', text):
            set_timer(int(m.group(1)), m.group(2).strip() or "Timer", self._timer_done)
        timer_info = ""
        if '[ACTION:TIMER_CHECK]' in text: timer_info = get_active_timers()
        for m in re.finditer(r'\[ACTION:TIMER_CANCEL\s*(.*?)\]', text): cancel_timer(m.group(1).strip() or None)

        # Search & Weather
        search_results = ""
        for m in re.finditer(r'\[ACTION:SEARCH\s+(.+?)\]', text):
            search_results = await web_search(m.group(1).strip())
        weather_info = ""
        for m in re.finditer(r'\[ACTION:WEATHER\s+(.+?)\]', text):
            weather_info = await get_weather(m.group(1).strip())

        # Screenshot
        screen_data = None
        if '[ACTION:SCREENSHOT]' in text and SETTINGS["enable_screen_capture"]:
            screen_data = capture_screen()

        # Focus
        if SETTINGS["enable_focus_mode"]:
            for m in re.finditer(r'\[ACTION:FOCUS\s+(\d+)\]', text):
                start_focus_mode(int(m.group(1))); set_timer(int(m.group(1)) * 60, "Focus", self._focus_done)
            if '[ACTION:FOCUS_END]' in text: end_focus_mode()
        focus_info = ""
        if '[ACTION:FOCUS_STATUS]' in text: focus_info = get_focus_status()

        # Notes
        for m in re.finditer(r'\[ACTION:NOTE\s+(.+?)\]', text): add_note(m.group(1).strip())
        notes_info = ""
        if '[ACTION:NOTES_READ]' in text: notes_info = get_recent_notes()
        for m in re.finditer(r'\[ACTION:NOTES_SEARCH\s+(.+?)\]', text): notes_info = search_notes(m.group(1).strip())
        if '[ACTION:NOTES_CLEAR]' in text: clear_notes()

        # System
        system_info = ""
        if '[ACTION:SYSTEM_STATUS]' in text: system_info = get_system_status()

        # Clipboard
        read_aloud = ""
        if '[ACTION:READ_CLIPBOARD]' in text: read_aloud = read_clipboard_aloud()

        # Smart rewrite
        rewrite_result = ""
        for m in re.finditer(r'\[ACTION:REWRITE_CLIPBOARD\s+(.+?)\]', text):
            clip = get_clipboard()
            if clip:
                rewritten = await self.llm.rewrite_text(clip, m.group(1).strip())
                set_clipboard(rewritten)
                rewrite_result = f"Rewritten and copied to clipboard."
            else:
                rewrite_result = "Nothing on clipboard."

        # Math
        math_info = ""
        for m in re.finditer(r'\[ACTION:MATH\s+(.+?)\]', text): math_info = evaluate_math(m.group(1).strip())

        # Convert
        convert_info = ""
        for m in re.finditer(r'\[ACTION:CONVERT\s+([\d.]+)\s+(\w+)\s+(\w+)\]', text):
            convert_info = convert_units(float(m.group(1)), m.group(2), m.group(3))

        # Countdown
        countdown_info = ""
        for m in re.finditer(r'\[ACTION:TIME_UNTIL\s+(.+?)\]', text): countdown_info = time_until(m.group(1).strip())

        # File finder
        file_info = ""
        if SETTINGS["enable_file_finder"]:
            for m in re.finditer(r'\[ACTION:FIND_FILE\s+(.+?)\]', text): file_info = find_file(m.group(1).strip())

        # Briefing
        briefing_info = ""
        if '[ACTION:BRIEFING]' in text: briefing_info = get_daily_briefing()

        # Trivia
        trivia_info = ""
        for m in re.finditer(r'\[ACTION:TRIVIA\s*(.+?)?\]', text):
            trivia_info = get_trivia(m.group(1).strip() if m.group(1) else "general")

        # Random
        random_info = ""
        if '[ACTION:COIN_FLIP]' in text: random_info = coin_flip()
        for m in re.finditer(r'\[ACTION:ROLL_DICE\s*(\d*)\]', text):
            random_info = roll_dice(int(m.group(1)) if m.group(1) else 6)
        for m in re.finditer(r'\[ACTION:RANDOM_NUMBER\s+(\d+)\s+(\d+)\]', text):
            random_info = random_number(int(m.group(1)), int(m.group(2)))

        # Strip tags
        clean = re.sub(r'\[ACTION:\w+.*?\]', '', text).strip()

        # Summarize fetched data
        extra = ""
        for label, val in [("Search", search_results), ("Weather", weather_info),
            ("Timers", timer_info), ("Focus", focus_info), ("Notes", notes_info),
            ("System", system_info), ("Spotify", spotify_info), ("Math", math_info),
            ("Conversion", convert_info), ("Countdown", countdown_info), ("Random", random_info),
            ("Files", file_info), ("Briefing", briefing_info), ("Trivia", trivia_info),
            ("Rewrite", rewrite_result)]:
            if val: extra += f"\n[{label}]: {val}"

        if extra:
            mood = get_mood_context()
            followup = await self.llm.chat(f"Report naturally in speech:{extra}", mood_hint=mood)
            clean = re.sub(r'\[ACTION:\w+.*?\]', '', followup).strip()
            clean = re.sub(r'\[REMEMBER\s+.+?\]', '', clean).strip()

        if screen_data:
            img_b64, mtype = screen_data
            vision = await self.llm.chat_with_image(
                "Describe screen briefly. If homework/math, solve step by step concisely.",
                img_b64, mtype, mood_hint=get_mood_context())
            clean = re.sub(r'\[ACTION:\w+.*?\]', '', vision).strip()
            clean = re.sub(r'\[REMEMBER\s+.+?\]', '', clean).strip()

        if read_aloud: clean = f"Reading your clipboard. {read_aloud}"
        return clean

    # ── Context ───────────────────────────────────────

    def _context(self, text):
        parts = []
        now = datetime.now()
        parts.append(f"Time: {now.strftime('%I:%M %p, %A %B %d %Y')}")
        parts.append(f"Session: {int((time.time() - self.start_time) / 60)}min, {self.commands_processed} cmds")
        if self.quiet_mode: parts.append("Quiet mode is ON (text-only, no voice)")
        if active_timers: parts.append(f"Timers: {get_active_timers()}")
        if focus_state["active"]: parts.append(f"Focus: {get_focus_status()}")
        memories = self.memory.recall(text, limit=3)
        if memories: parts.append("Memory: " + "; ".join(f"{m['key']}: {m['value']}" for m in memories))
        clip_kw = ["clipboard", "copied", "copy", "paste", "what i copied",
                    "summarize this", "read my clipboard", "read aloud", "proofread", "rewrite"]
        if any(k in text.lower() for k in clip_kw):
            clip = get_clipboard()
            if clip: parts.append(f"Clipboard: {clip[:500]}")
        return "\n".join(parts)

    # ── Process ───────────────────────────────────────

    def _is_shutdown(self, text):
        return any(p in text.lower() for p in [
            "shut down", "shutdown", "power off", "goodbye jarvis",
            "goodbye", "go to sleep", "dismiss", "good night"])

    def _check_quiet_mode(self, text):
        t = text.lower()
        if any(p in t for p in ["quiet mode", "silent mode", "text mode", "mute yourself"]):
            self.quiet_mode = True
            return "Quiet mode on. I'll respond in text only."
        if any(p in t for p in ["voice mode", "speak again", "unmute yourself", "talk again"]):
            self.quiet_mode = False
            return "Voice mode restored."
        return None

    async def _process(self, audio):
        text = self.stt.transcribe(audio)
        if not text: self._play_sound(self._error_chime); return False

        print(f"\n[You] {text}")
        self.commands_processed += 1

        # Easter eggs
        if SETTINGS["enable_easter_eggs"]:
            egg = check_easter_egg(text)
            if egg:
                print(f"[JARVIS] {egg}")
                _log_interaction(text, egg)
                await self._speak(egg)
                return True

        # Quiet mode toggle
        qm = self._check_quiet_mode(text)
        if qm:
            print(f"[JARVIS] {qm}")
            _log_interaction(text, qm)
            await self._speak(qm)
            return True

        # Repeat
        if any(p in text.lower() for p in ["repeat that", "say that again", "what did you say"]):
            if self.last_response:
                _log_interaction(text, self.last_response)
                await self._speak(self.last_response)
            return True

        # Shutdown
        if self._is_shutdown(text):
            up = int((time.time() - self.start_time) / 60)
            msg = f"Shutting down after {up} minutes and {self.commands_processed} commands. Until next time."
            _log_interaction(text, msg)
            await self._speak(msg)
            self._play_sound(self._shutdown_chime)
            self.should_shutdown = True
            return False

        # Fast-path (instant, no LLM)
        fast = _check_fast_path(text)
        if fast:
            print(f"[JARVIS] (fast) {fast}")
            _log_interaction(text, fast)
            await self._speak(fast)
            return True

        # Full LLM path
        self._play_sound(self._think_chime)
        ctx = self._context(text)
        mood = get_mood_context()
        raw = await self.llm.chat(text, memory_context=ctx, mood_hint=mood)

        clean, mems = extract_memories(raw)
        for k, v in mems: self.memory.remember(k, v)

        # Quick ack for slow actions
        if self._needs_quick_ack(clean):
            await self._quick_ack()

        final = await self._process_actions(clean)
        self.last_response = final
        _log_interaction(text, final)
        print(f"[JARVIS] {final}")
        await self._speak(final)
        return True

    # ── Startup ───────────────────────────────────────

    def _greet(self):
        if not SETTINGS["startup_greeting"]:
            print("[JARVIS] Startup greeting disabled. Ready.")
            return

        h = datetime.now().hour
        g = "Good morning" if h < 12 else ("Good afternoon" if h < 17 else "Good evening")
        name = SETTINGS["user_name"]
        greetings = [
            f"{g}, {name}. JARVIS is online and ready.",
            f"{g}, {name}. All systems nominal.",
            f"{g}, {name}. At your service.",
            f"{g}, {name}. Systems initialized. What shall we tackle?",
            f"{g}, {name}. Standing by.",
        ]
        text = random.choice(greetings)
        print(f"[JARVIS] {text}")
        asyncio.run(self._speak(text))

    # ── Main Loop ─────────────────────────────────────

    def run(self):
        self._greet()
        print("\nLoading wake word model...")
        wm = WakeModel(wakeword_models=["hey_jarvis"], inference_framework="onnx")
        print('Listening for "Hey JARVIS"...\n')

        stream = self.audio.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)
        battery_check_interval = 300  # Check every 5 min
        last_battery_check = time.time()

        while True:
            try:
                if self.is_speaking: stream.read(CHUNK, exception_on_overflow=False); continue

                # Periodic battery check
                if time.time() - last_battery_check > battery_check_interval:
                    last_battery_check = time.time()
                    self._check_battery()

                data = stream.read(CHUNK, exception_on_overflow=False)
                pred = wm.predict(np.array(struct.unpack(f'{CHUNK}h', data), dtype=np.int16))

                for name, score in pred.items():
                    if score > 0.5:
                        print("\n[Wake] JARVIS activated!")
                        stream.stop_stream(); self._play_sound(self._chime)
                        convo = True
                        ok = asyncio.run(self._process(self._record()))

                        # Resume Spotify if it was paused
                        if not self.should_shutdown:
                            self._resume_spotify()

                        if self.should_shutdown: stream.close(); self.audio.terminate(); return

                        while convo and ok:
                            fu = self._followup(CONVERSATION_TIMEOUT)
                            if fu is None:
                                print("[Conversation] Standby.")
                                convo = False
                                self._resume_spotify()
                            else:
                                ok = asyncio.run(self._process(fu))
                                if self.should_shutdown: stream.close(); self.audio.terminate(); return

                        stream.start_stream(); wm.reset()
                        print('\nListening for "Hey JARVIS"...\n')

            except KeyboardInterrupt:
                print("\n[JARVIS] Force shutdown.")
                stream.stop_stream(); stream.close(); self.audio.terminate(); break
            except Exception as e:
                print(f"[Error] {e}")
                time.sleep(1)


if __name__ == "__main__":
    while True:
        try:
            VoiceAssistant().run()
            break  # Clean shutdown
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"\n[CRASH] {e}")
            print("[JARVIS] Restarting in 3 seconds...")
            time.sleep(3)
