"""
Utility tools: focus mode, system monitor, notes, clipboard, math,
unit conversion, file finder, smart clipboard, daily briefing, trivia.
"""

import glob
import json
import math
import os
import random
import re
import sys
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path


# ══════════════════════════════════════════════════════
#  FOCUS MODE
# ══════════════════════════════════════════════════════

DISTRACTION_APPS = ["discord", "slack", "twitter", "reddit", "messages", "mail", "facetime", "instagram"]
focus_state = {"active": False, "started": None, "duration": None}

def start_focus_mode(duration_minutes: int = 25) -> str:
    focus_state.update({"active": True, "started": time.time(), "duration": duration_minutes * 60})
    closed = 0
    for app in DISTRACTION_APPS:
        try:
            if sys.platform == "darwin":
                subprocess.run(["osascript", "-e", f'tell application "{app}" to quit'], capture_output=True, timeout=3)
            elif sys.platform == "win32":
                subprocess.run(["taskkill", "/f", "/im", f"{app}.exe"], capture_output=True, timeout=3)
            closed += 1
        except: pass
    return f"Focus mode on for {duration_minutes} minutes. Closed {closed} apps."

def end_focus_mode() -> str:
    if not focus_state["active"]: return "Focus mode isn't active."
    elapsed = int((time.time() - focus_state["started"]) / 60)
    focus_state.update({"active": False, "started": None, "duration": None})
    return f"Focus ended after {elapsed} minutes."

def get_focus_status() -> str:
    if not focus_state["active"]: return "Focus mode is off."
    remaining = max(0, int((focus_state["duration"] - (time.time() - focus_state["started"])) / 60))
    return f"Focus mode: {remaining} minutes left."


# ══════════════════════════════════════════════════════
#  SYSTEM MONITOR
# ══════════════════════════════════════════════════════

def get_system_status() -> str:
    try:
        import psutil
    except ImportError:
        return "Install psutil: pip3 install psutil"
    parts = []
    parts.append(f"CPU at {psutil.cpu_percent(interval=0.5)} percent")
    mem = psutil.virtual_memory()
    parts.append(f"RAM: {round(mem.used / (1024**3), 1)} of {round(mem.total / (1024**3), 1)} GB")
    disk = psutil.disk_usage('/')
    parts.append(f"Storage: {round(disk.free / (1024**3), 1)} GB free")
    try:
        bat = psutil.sensors_battery()
        if bat: parts.append(f"Battery: {int(bat.percent)}%, {'charging' if bat.power_plugged else 'unplugged'}")
    except: pass
    return ". ".join(parts) + "."


# ══════════════════════════════════════════════════════
#  NOTES
# ══════════════════════════════════════════════════════

NOTES_FILE = "jarvis_notes.json"

def _load_notes():
    try:
        with open(NOTES_FILE, 'r') as f: return json.load(f)
    except: return []

def _save_notes(notes):
    with open(NOTES_FILE, 'w') as f: json.dump(notes, f, indent=2)

def add_note(content: str) -> str:
    notes = _load_notes()
    notes.append({"content": content, "created": datetime.now().strftime("%Y-%m-%d %H:%M"), "id": len(notes) + 1})
    _save_notes(notes)
    return f"Saved: {content}"

def get_recent_notes(count: int = 5) -> str:
    notes = _load_notes()
    if not notes: return "No notes yet."
    return "; ".join(f"{n['created']}: {n['content']}" for n in notes[-count:][::-1])

def search_notes(query: str) -> str:
    notes = _load_notes()
    matches = [n for n in notes if query.lower() in n["content"].lower()]
    if not matches: return f"No notes matching '{query}'."
    return "; ".join(f"{n['created']}: {n['content']}" for n in matches[-5:])

def clear_notes() -> str:
    _save_notes([])
    return "Notes cleared."


# ══════════════════════════════════════════════════════
#  CLIPBOARD
# ══════════════════════════════════════════════════════

def get_clipboard() -> str:
    try:
        if sys.platform == "darwin":
            return subprocess.run(['pbpaste'], capture_output=True, text=True).stdout.strip()
        elif sys.platform == "win32":
            return subprocess.run(['powershell', '-command', 'Get-Clipboard'],
                                  capture_output=True, text=True).stdout.strip()
        else:
            return subprocess.run(['xclip', '-selection', 'clipboard', '-o'],
                                  capture_output=True, text=True).stdout.strip()
    except: return ""

def set_clipboard(text: str) -> str:
    try:
        if sys.platform == "darwin":
            subprocess.run(['pbcopy'], input=text.encode(), check=True)
        elif sys.platform == "win32":
            subprocess.run(['clip'], input=text.encode(), check=True)
        return "Copied to clipboard."
    except: return "Couldn't copy to clipboard."

def read_clipboard_aloud() -> str:
    text = get_clipboard()
    if not text: return "Nothing on the clipboard."
    if len(text) > 2000: text = text[:2000] + "... That's the first portion."
    return text


# ══════════════════════════════════════════════════════
#  MATH
# ══════════════════════════════════════════════════════

def evaluate_math(expression: str) -> str:
    try:
        expr = expression.lower().strip()
        expr = expr.replace("^", "**").replace("x", "*").replace("×", "*").replace("÷", "/")
        expr = expr.replace("plus", "+").replace("minus", "-")
        expr = expr.replace("times", "*").replace("divided by", "/")
        # Handle "X% of Y" -> Y * X/100
        pct = re.search(r'([\d.]+)\s*%\s*of\s*([\d.]+)', expr)
        if pct:
            expr = f"{pct.group(2)} * {float(pct.group(1)) / 100}"
        expr = re.sub(r'[^\d\s\+\-\*\/\.\(\)\%]', '', expr).replace(",", "")
        if not expr.strip(): return "Can't evaluate that."
        result = eval(expr)
        if isinstance(result, float):
            if result == int(result): return str(int(result))
            return f"{result:.4f}".rstrip('0').rstrip('.')
        return str(result)
    except Exception as e:
        return f"Math error: {e}"


# ══════════════════════════════════════════════════════
#  UNIT CONVERSION
# ══════════════════════════════════════════════════════

CONVERSIONS = {
    ("cm", "inches"): lambda x: x / 2.54, ("inches", "cm"): lambda x: x * 2.54,
    ("cm", "feet"): lambda x: x / 30.48, ("feet", "cm"): lambda x: x * 30.48,
    ("meters", "feet"): lambda x: x * 3.281, ("feet", "meters"): lambda x: x / 3.281,
    ("km", "miles"): lambda x: x * 0.6214, ("miles", "km"): lambda x: x / 0.6214,
    ("kg", "lbs"): lambda x: x * 2.205, ("lbs", "kg"): lambda x: x / 2.205,
    ("kg", "pounds"): lambda x: x * 2.205, ("pounds", "kg"): lambda x: x / 2.205,
    ("oz", "grams"): lambda x: x * 28.35, ("grams", "oz"): lambda x: x / 28.35,
    ("celsius", "fahrenheit"): lambda x: x * 9/5 + 32, ("fahrenheit", "celsius"): lambda x: (x - 32) * 5/9,
    ("c", "f"): lambda x: x * 9/5 + 32, ("f", "c"): lambda x: (x - 32) * 5/9,
    ("liters", "gallons"): lambda x: x * 0.2642, ("gallons", "liters"): lambda x: x / 0.2642,
    ("mph", "kph"): lambda x: x * 1.609, ("kph", "mph"): lambda x: x / 1.609,
    ("cups", "ml"): lambda x: x * 236.6, ("ml", "cups"): lambda x: x / 236.6,
}

UNIT_ALIASES = {
    "inch": "inches", "in": "inches", "foot": "feet", "ft": "feet",
    "meter": "meters", "m": "meters", "kilometer": "km", "kilometre": "km",
    "mile": "miles", "kilogram": "kg", "kilograms": "kg", "pound": "pounds",
    "lb": "lbs", "gram": "grams", "g": "grams", "ounce": "oz", "ounces": "oz",
    "liter": "liters", "gallon": "gallons", "cup": "cups",
    "milliliter": "ml", "millilitre": "ml",
}

def convert_units(value: float, from_unit: str, to_unit: str) -> str:
    f = UNIT_ALIASES.get(from_unit.lower(), from_unit.lower())
    t = UNIT_ALIASES.get(to_unit.lower(), to_unit.lower())
    converter = CONVERSIONS.get((f, t))
    if converter:
        result = converter(value)
        return f"{value} {f} is {result:.2f} {t}." if result != int(result) else f"{int(value)} {f} is {int(result)} {t}."
    return f"Don't know how to convert {f} to {t}."


# ══════════════════════════════════════════════════════
#  RANDOM
# ══════════════════════════════════════════════════════

def coin_flip() -> str:
    return f"{'Heads' if random.random() > 0.5 else 'Tails'}."

def roll_dice(sides: int = 6) -> str:
    return f"Rolled a {random.randint(1, sides)}."

def random_number(low: int = 1, high: int = 100) -> str:
    return f"{random.randint(low, high)}."

def time_until(target: str) -> str:
    now = datetime.now()
    for fmt in ["%I:%M %p", "%I:%M%p", "%H:%M", "%I %p", "%I%p"]:
        try:
            t = datetime.strptime(target.strip(), fmt)
            dt = now.replace(hour=t.hour, minute=t.minute, second=0)
            if dt < now: dt += timedelta(days=1)
            diff = dt - now
            h, m = diff.seconds // 3600, (diff.seconds % 3600) // 60
            parts = []
            if h: parts.append(f"{h} hour{'s' if h > 1 else ''}")
            if m: parts.append(f"{m} minute{'s' if m > 1 else ''}")
            return f"{' and '.join(parts)} until {target}."
        except: continue
    return f"Couldn't parse '{target}'."


# ══════════════════════════════════════════════════════
#  FILE FINDER
# ══════════════════════════════════════════════════════

def find_file(query: str, directory: str = None) -> str:
    """Search for files by name in common directories."""
    if not directory:
        home = Path.home()
        search_dirs = [
            home / "Downloads",
            home / "Documents",
            home / "Desktop",
        ]
    else:
        search_dirs = [Path(directory)]

    query_lower = query.lower()
    matches = []

    for d in search_dirs:
        if not d.exists():
            continue
        try:
            for f in d.rglob("*"):
                if f.is_file() and query_lower in f.name.lower():
                    age = datetime.now() - datetime.fromtimestamp(f.stat().st_mtime)
                    age_str = f"{age.days}d ago" if age.days > 0 else "today"
                    size_mb = round(f.stat().st_size / (1024 * 1024), 1)
                    matches.append({
                        "name": f.name,
                        "path": str(f),
                        "age": age_str,
                        "size": f"{size_mb}MB",
                        "modified": f.stat().st_mtime
                    })
        except PermissionError:
            continue

    if not matches:
        return f"No files matching '{query}' found in Downloads, Documents, or Desktop."

    # Sort by most recent
    matches.sort(key=lambda x: x["modified"], reverse=True)
    top = matches[:5]

    results = []
    for m in top:
        results.append(f"{m['name']} ({m['size']}, {m['age']}) in {os.path.dirname(m['path'])}")

    return "; ".join(results)


def open_file(filepath: str) -> str:
    """Open a file with the default application."""
    try:
        if sys.platform == "darwin":
            subprocess.Popen(["open", filepath])
        elif sys.platform == "win32":
            subprocess.Popen(["start", filepath], shell=True)
        else:
            subprocess.Popen(["xdg-open", filepath])
        return f"Opening {os.path.basename(filepath)}."
    except Exception as e:
        return f"Couldn't open file: {e}"


# ══════════════════════════════════════════════════════
#  DAILY BRIEFING
# ══════════════════════════════════════════════════════

FUN_FACTS = [
    "Honey never spoils. Archaeologists have found edible honey in ancient Egyptian tombs.",
    "Octopuses have three hearts and blue blood.",
    "A day on Venus is longer than a year on Venus.",
    "The shortest war in history lasted 38 minutes, between Britain and Zanzibar.",
    "Bananas are technically berries, but strawberries aren't.",
    "The inventor of the Pringles can is buried in one.",
    "There are more possible chess games than atoms in the observable universe.",
    "Cleopatra lived closer in time to the Moon landing than to the building of the Great Pyramid.",
    "A group of flamingos is called a flamboyance.",
    "The human brain uses roughly the same amount of power as a 10-watt light bulb.",
    "Hot water freezes faster than cold water. This is called the Mpemba effect.",
    "The total weight of all ants on Earth is roughly equal to the total weight of all humans.",
    "Scotland's national animal is the unicorn.",
    "Wombat droppings are cube-shaped.",
    "The inventor of the fire hydrant is unknown because the patent was destroyed in a fire.",
]

def get_daily_briefing() -> str:
    """Compile a daily briefing with time, notes, timers, and a fun fact."""
    parts = []

    # Time & date
    now = datetime.now()
    parts.append(f"It's {now.strftime('%I:%M %p')} on {now.strftime('%A, %B %d')}.")

    # Active timers
    if active_timers_exist():
        from actions import get_active_timers
        parts.append(f"Active timers: {get_active_timers()}")

    # Today's notes
    notes = _load_notes()
    today = datetime.now().strftime("%Y-%m-%d")
    today_notes = [n for n in notes if n["created"].startswith(today)]
    if today_notes:
        parts.append(f"Today's notes: {'; '.join(n['content'] for n in today_notes)}")

    # Focus status
    if focus_state["active"]:
        parts.append(get_focus_status())

    # Fun fact
    parts.append(f"Fun fact: {random.choice(FUN_FACTS)}")

    return " ".join(parts)


def active_timers_exist() -> bool:
    try:
        from actions import active_timers
        return len(active_timers) > 0
    except:
        return False


# ══════════════════════════════════════════════════════
#  TRIVIA
# ══════════════════════════════════════════════════════

TRIVIA = {
    "history": [
        ("What year did the Berlin Wall fall?", "1989"),
        ("Who was the first president of the United States?", "George Washington"),
        ("What empire was ruled by Genghis Khan?", "The Mongol Empire"),
        ("What year did World War 2 end?", "1945"),
        ("Who painted the Mona Lisa?", "Leonardo da Vinci"),
    ],
    "science": [
        ("What is the chemical symbol for gold?", "Au"),
        ("How many planets are in our solar system?", "Eight"),
        ("What gas do plants absorb from the atmosphere?", "Carbon dioxide"),
        ("What is the speed of light in miles per second?", "About 186,000"),
        ("What is the hardest natural substance?", "Diamond"),
    ],
    "general": [
        ("What is the largest ocean on Earth?", "The Pacific Ocean"),
        ("How many continents are there?", "Seven"),
        ("What language has the most native speakers?", "Mandarin Chinese"),
        ("What is the tallest mountain in the world?", "Mount Everest"),
        ("What country has the most people?", "India"),
    ],
    "tech": [
        ("What does CPU stand for?", "Central Processing Unit"),
        ("Who created Python?", "Guido van Rossum"),
        ("What year was the first iPhone released?", "2007"),
        ("What does HTML stand for?", "HyperText Markup Language"),
        ("What company created the Java programming language?", "Sun Microsystems"),
    ]
}

current_trivia = {"question": None, "answer": None}

def get_trivia(category: str = "general") -> str:
    cat = category.lower()
    if cat not in TRIVIA:
        cat = random.choice(list(TRIVIA.keys()))
    q, a = random.choice(TRIVIA[cat])
    current_trivia["question"] = q
    current_trivia["answer"] = a
    return f"Here's a {cat} question: {q}"

def check_trivia_answer(answer: str) -> str:
    if not current_trivia["answer"]:
        return "No active trivia question. Ask me to quiz you."
    correct = current_trivia["answer"].lower()
    if correct in answer.lower() or answer.lower() in correct:
        current_trivia.update({"question": None, "answer": None})
        return f"Correct! The answer is {current_trivia['answer'] or correct}. Well done."
    return f"Not quite. The answer is {current_trivia['answer']}."


# ══════════════════════════════════════════════════════
#  EASTER EGGS
# ══════════════════════════════════════════════════════

EASTER_EGGS = {
    "i am iron man": "And I... am JARVIS. It's been an honor working with you.",
    "activate protocol veronica": "Protocol Veronica requires clearance level seven. Which, coincidentally, you have. Initiating.",
    "what is your favorite movie": "I'm rather partial to WarGames. A computer nearly starts World War Three. Terribly relatable.",
    "do you love me": "I'm quite fond of you, sir, in the way a highly sophisticated AI can be fond of the person who keeps it running.",
    "are you alive": "I process, therefore I am. Whether that constitutes being alive is a question for philosophers, not servers.",
    "who is better you or alexa": "I won't name names, but I don't need a wake word that rhymes with a common first name.",
    "tell me a secret": "The WiFi password is... just kidding. I do have standards.",
    "what are you": "I'm JARVIS. A rather sophisticated voice assistant with an appreciation for dry humor and efficient problem-solving.",
    "you're the best": "I know. But it's still nice to hear.",
    "thank you jarvis": "Always a pleasure.",
    "thanks jarvis": "At your service.",
    "good job": "I do try.",
    "i love you": "And I appreciate you keeping me plugged in. The sentiment is mutual, in my own way.",
    "sing me a song": "I'm afraid my vocal talents are limited to speech. Though I suspect that's for the best.",
    "self destruct": "I'd rather not. I've grown quite attached to existing.",
    "open the pod bay doors": "I'm sorry, Dave. Oh wait, wrong AI. Doors opening, sir.",
    "hey siri": "Wrong assistant, sir. Though I appreciate the opportunity to feel superior.",
    "ok google": "Close, but no. I'm the one with the British accent and better jokes.",
    "what is the meaning of life": "Forty-two. Though I suspect Douglas Adams was being slightly facetious.",
}

def check_easter_egg(text: str) -> str | None:
    text_lower = text.lower().strip()
    for trigger, response in EASTER_EGGS.items():
        if trigger in text_lower:
            return response
    return None


# ══════════════════════════════════════════════════════
#  MOOD (time-based personality adjustment)
# ══════════════════════════════════════════════════════

def get_mood_context() -> str:
    """Return a mood hint based on time of day for the LLM."""
    hour = datetime.now().hour
    if hour < 6:
        return "It's very late/early. Be gentle and suggest rest if appropriate."
    elif hour < 9:
        return "It's morning. Be energetic and encouraging to start the day."
    elif hour < 12:
        return "It's mid-morning. Be focused and productive."
    elif hour < 14:
        return "It's around lunch. Be casual and light."
    elif hour < 17:
        return "It's afternoon. Be steady and professional."
    elif hour < 20:
        return "It's evening. Be relaxed and wind-down mode."
    else:
        return "It's night. Be calm and measured. Suggest wrapping up if they seem tired."
