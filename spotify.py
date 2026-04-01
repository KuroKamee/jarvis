"""
Cross-platform Spotify control.
Uses DuckDuckGo to find Spotify track URLs, then plays directly.
"""

import re
import subprocess
import sys
import time


def _press_media_key(key_name: str) -> bool:
    try:
        from pynput.keyboard import Key, Controller
        kb = Controller()
        key_map = {"play_pause": Key.media_play_pause, "next": Key.media_next, "previous": Key.media_previous}
        key = key_map.get(key_name)
        if key: kb.press(key); kb.release(key); return True
    except: pass
    return False

def _osascript(script: str) -> str:
    try: return subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=5).stdout.strip()
    except: return ""

def _open_spotify():
    try:
        if sys.platform == "darwin": subprocess.Popen(["open", "-a", "Spotify"])
        elif sys.platform == "win32": subprocess.Popen(["start", "spotify:"], shell=True)
        else: subprocess.Popen(["spotify"])
    except: pass

def _find_spotify_url(query: str) -> str | None:
    try:
        try:
            from ddgs import DDGS
        except ImportError:
            from duckduckgo_search import DDGS
        for q in [f"site:open.spotify.com {query}", f"spotify {query}"]:
            with DDGS() as ddgs:
                for r in ddgs.text(q, max_results=5):
                    url = r.get("href", "") or r.get("link", "")
                    if "open.spotify.com" in url: return url
    except Exception as e:
        print(f"[Spotify] Search error: {e}")
    return None

def _url_to_uri(url: str) -> str:
    match = re.search(r'open\.spotify\.com/(track|artist|album|playlist)/([a-zA-Z0-9]+)', url)
    if match: return f"spotify:{match.group(1)}:{match.group(2)}"
    return url

def spotify_play(query: str) -> str:
    print(f"  [Spotify] Searching: {query}")
    url = _find_spotify_url(query)
    if url:
        uri = _url_to_uri(url)
        _open_spotify(); time.sleep(1)
        try:
            if sys.platform == "darwin":
                if "track" in uri or "album" in uri or "playlist" in uri:
                    _osascript(f'tell application "Spotify" to play track "{uri}"')
                else:
                    subprocess.Popen(["open", uri]); time.sleep(2)
                    _osascript('tell application "Spotify" to play')
            elif sys.platform == "win32":
                subprocess.Popen(["start", uri], shell=True)
            else:
                subprocess.Popen(["xdg-open", url])
            return f"Playing {query}."
        except Exception as e:
            return f"Found but couldn't play: {e}"
    else:
        _open_spotify(); time.sleep(1)
        import urllib.parse
        try:
            uri = f"spotify:search:{urllib.parse.quote(query)}"
            if sys.platform == "darwin": subprocess.Popen(["open", uri])
            elif sys.platform == "win32": subprocess.Popen(["start", uri], shell=True)
            return f"Searched for {query} on Spotify. You may need to press play."
        except:
            return f"Couldn't find {query}."

def spotify_play_pause() -> str:
    if sys.platform == "darwin": _osascript('tell application "Spotify" to playpause'); return "Toggling playback."
    _press_media_key("play_pause"); return "Toggling playback."

def spotify_next() -> str:
    if sys.platform == "darwin": _osascript('tell application "Spotify" to next track'); return "Next track."
    _press_media_key("next"); return "Next track."

def spotify_previous() -> str:
    if sys.platform == "darwin": _osascript('tell application "Spotify" to previous track'); return "Previous track."
    _press_media_key("previous"); return "Previous track."

def spotify_get_current() -> str:
    if sys.platform == "darwin":
        name = _osascript('tell application "Spotify" to name of current track')
        artist = _osascript('tell application "Spotify" to artist of current track')
        if name and artist: return f"Now playing: {name} by {artist}."
        return "Nothing playing."
    return "Track info available on Mac only."

def spotify_shuffle_on() -> str:
    if sys.platform == "darwin": _osascript('tell application "Spotify" to set shuffling to true'); return "Shuffle on."
    return "Shuffle requires Mac."

def spotify_repeat() -> str:
    if sys.platform == "darwin":
        cur = _osascript('tell application "Spotify" to repeating')
        _osascript(f'tell application "Spotify" to set repeating to {"false" if cur == "true" else "true"}')
        return "Repeat toggled."
    return "Repeat requires Mac."

def spotify_set_volume(level: int) -> str:
    if sys.platform == "darwin": _osascript(f'tell application "Spotify" to set sound volume to {level}'); return f"Spotify volume at {level}."
    return "Spotify volume requires Mac."
