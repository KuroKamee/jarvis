"""
Cross-platform system actions: app launcher, volume, timers, screen capture.
Works on macOS, Windows, and Linux.
"""

import base64
import os
import re
import subprocess
import sys
import tempfile
import threading
import time


# ══════════════════════════════════════════════════════
#  APP LAUNCHER (cross-platform)
# ══════════════════════════════════════════════════════

APP_ALIASES_MAC = {
    "chrome": "Google Chrome", "safari": "Safari", "firefox": "Firefox",
    "spotify": "Spotify", "music": "Music", "notes": "Notes",
    "messages": "Messages", "mail": "Mail", "calendar": "Calendar",
    "finder": "Finder", "terminal": "Terminal", "slack": "Slack",
    "discord": "Discord", "zoom": "zoom.us", "teams": "Microsoft Teams",
    "word": "Microsoft Word", "excel": "Microsoft Excel",
    "vscode": "Visual Studio Code", "vs code": "Visual Studio Code",
    "code": "Visual Studio Code", "photos": "Photos",
    "calculator": "Calculator", "maps": "Maps",
}

APP_ALIASES_WIN = {
    "chrome": "chrome", "firefox": "firefox", "edge": "msedge",
    "spotify": "spotify", "notepad": "notepad", "calculator": "calc",
    "mail": "outlook", "calendar": "outlook", "word": "winword",
    "excel": "excel", "powerpoint": "powerpnt", "explorer": "explorer",
    "vscode": "code", "vs code": "code", "code": "code",
    "discord": "discord", "slack": "slack", "teams": "teams",
    "terminal": "wt", "cmd": "cmd", "powershell": "powershell",
}

# URLs for apps that are better opened in browser
WEB_APPS = {
    "youtube": "https://youtube.com",
    "gmail": "https://gmail.com",
    "google docs": "https://docs.google.com",
    "google drive": "https://drive.google.com",
    "github": "https://github.com",
    "twitter": "https://twitter.com",
    "reddit": "https://reddit.com",
}


def open_app(app_name: str) -> str:
    name_lower = app_name.lower().strip()

    # Check web apps first
    if name_lower in WEB_APPS:
        import webbrowser
        webbrowser.open(WEB_APPS[name_lower])
        return f"Opening {app_name} in your browser."

    try:
        if sys.platform == "darwin":
            resolved = APP_ALIASES_MAC.get(name_lower, app_name)
            subprocess.Popen(["open", "-a", resolved])
            return f"Opening {resolved}."
        elif sys.platform == "win32":
            resolved = APP_ALIASES_WIN.get(name_lower, app_name)
            subprocess.Popen(["start", resolved], shell=True)
            return f"Opening {resolved}."
        else:
            subprocess.Popen([app_name.lower()])
            return f"Opening {app_name}."
    except Exception as e:
        return f"Couldn't open {app_name}: {e}"


def close_app(app_name: str) -> str:
    name_lower = app_name.lower().strip()

    try:
        if sys.platform == "darwin":
            resolved = APP_ALIASES_MAC.get(name_lower, app_name)
            subprocess.run(["osascript", "-e", f'tell application "{resolved}" to quit'],
                           capture_output=True)
            return f"Closing {resolved}."
        elif sys.platform == "win32":
            resolved = APP_ALIASES_WIN.get(name_lower, app_name)
            subprocess.run(["taskkill", "/f", "/im", f"{resolved}.exe"],
                           capture_output=True)
            return f"Closing {resolved}."
        else:
            subprocess.run(["pkill", "-f", app_name], capture_output=True)
            return f"Closing {app_name}."
    except Exception as e:
        return f"Couldn't close {app_name}: {e}"


# ══════════════════════════════════════════════════════
#  VOLUME CONTROL (cross-platform via media keys)
# ══════════════════════════════════════════════════════

def _media_key(key_name: str):
    try:
        from pynput.keyboard import Key, Controller
        kb = Controller()
        key_map = {
            "volume_up": Key.media_volume_up,
            "volume_down": Key.media_volume_down,
            "mute": Key.media_volume_mute,
        }
        key = key_map.get(key_name)
        if key:
            kb.press(key)
            kb.release(key)
    except:
        pass


def volume_up(steps: int = 5) -> str:
    for _ in range(steps):
        _media_key("volume_up")
    return "Volume increased."


def volume_down(steps: int = 5) -> str:
    for _ in range(steps):
        _media_key("volume_down")
    return "Volume decreased."


def mute() -> str:
    _media_key("mute")
    return "Audio muted."


def unmute() -> str:
    _media_key("mute")  # toggle
    return "Audio unmuted."


# ══════════════════════════════════════════════════════
#  TIMERS
# ══════════════════════════════════════════════════════

active_timers: list[dict] = []


def _timer_callback(name: str, seconds: int, sound_callback):
    time.sleep(seconds)
    active_timers[:] = [t for t in active_timers if t["name"] != name]
    print(f"\n[Timer] '{name}' finished!")
    if sound_callback:
        sound_callback(name)


def set_timer(duration_seconds: int, name: str = "Timer", sound_callback=None) -> str:
    thread = threading.Thread(
        target=_timer_callback,
        args=(name, duration_seconds, sound_callback),
        daemon=True
    )
    active_timers.append({
        "name": name, "duration": duration_seconds,
        "started": time.time(), "thread": thread
    })
    thread.start()

    if duration_seconds >= 3600:
        h = duration_seconds // 3600
        m = (duration_seconds % 3600) // 60
        dur = f"{h} hour{'s' if h > 1 else ''}"
        if m: dur += f" and {m} minute{'s' if m > 1 else ''}"
    elif duration_seconds >= 60:
        m = duration_seconds // 60
        s = duration_seconds % 60
        dur = f"{m} minute{'s' if m > 1 else ''}"
        if s: dur += f" and {s} second{'s' if s > 1 else ''}"
    else:
        dur = f"{duration_seconds} second{'s' if duration_seconds > 1 else ''}"

    return f"Timer set for {dur}."


def get_active_timers() -> str:
    if not active_timers:
        return "No active timers."
    parts = []
    for t in active_timers:
        remaining = max(0, t["duration"] - (time.time() - t["started"]))
        parts.append(f"{t['name']}: {int(remaining // 60)}m {int(remaining % 60)}s left")
    return "; ".join(parts)


def cancel_timer(name: str = None) -> str:
    if name:
        active_timers[:] = [t for t in active_timers if t["name"].lower() != name.lower()]
        return f"Timer '{name}' cancelled."
    active_timers.clear()
    return "All timers cancelled."


def parse_duration(text: str) -> int | None:
    text = text.lower()
    total = 0
    for match, mult in [(r'(\d+)\s*(?:hour|hr)s?', 3600),
                          (r'(\d+)\s*(?:minute|min)s?', 60),
                          (r'(\d+)\s*(?:second|sec)s?', 1)]:
        m = re.search(match, text)
        if m: total += int(m.group(1)) * mult
    if total == 0:
        m = re.search(r'(\d+)', text)
        if m: total = int(m.group(1)) * 60
    return total if total > 0 else None


# ══════════════════════════════════════════════════════
#  SCREEN CAPTURE (cross-platform)
# ══════════════════════════════════════════════════════

def capture_screen() -> tuple | None:
    """Returns (base64_image, media_type) or None."""
    try:
        from PIL import ImageGrab, Image

        # Capture screen
        img = ImageGrab.grab()

        # Resize for efficiency
        if img.width > 1024:
            ratio = 1024 / img.width
            img = img.resize((1024, int(img.height * ratio)))

        # Save as JPEG
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
            img.save(f, 'JPEG', quality=70)
            temp_path = f.name

        with open(temp_path, 'rb') as f:
            image_data = base64.b64encode(f.read()).decode('utf-8')

        os.unlink(temp_path)
        return (image_data, "image/jpeg")

    except ImportError:
        # Fallback for macOS without Pillow ImageGrab support
        try:
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
                temp_path = f.name

            if sys.platform == "darwin":
                subprocess.run(["screencapture", "-x", "-C", temp_path], capture_output=True)
            else:
                return None

            if not os.path.exists(temp_path):
                return None

            with open(temp_path, 'rb') as f:
                image_data = base64.b64encode(f.read()).decode('utf-8')

            os.unlink(temp_path)
            return (image_data, "image/png")
        except:
            return None
    except Exception as e:
        print(f"[Screen] Error: {e}")
        return None
