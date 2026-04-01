"""
J.A.R.V.I.S. — Settings Manager
Run standalone: python3 settings.py
Or import: from settings import load_settings
"""

import json
import os
import sys

SETTINGS_FILE = "jarvis_settings.json"

# Default settings with descriptions
DEFAULTS = {
    # Voice & Listening
    "whisper_model": {
        "value": "base.en",
        "description": "Speech recognition model",
        "options": ["tiny.en", "base.en", "small.en"],
        "help": "tiny.en = fastest but less accurate, base.en = balanced, small.en = best accuracy but slower"
    },
    "silence_seconds": {
        "value": 1.5,
        "description": "Seconds of silence before JARVIS stops recording",
        "range": [0.5, 3.0],
        "help": "Lower = faster response but might cut you off. Higher = more patient but slower."
    },
    "conversation_timeout": {
        "value": 6,
        "description": "Seconds to wait for follow-up before going to standby",
        "range": [3, 15],
        "help": "How long JARVIS waits for you to say something else before going back to sleep."
    },
    "interrupt_threshold": {
        "value": 2000,
        "description": "How loud you need to be to interrupt JARVIS",
        "range": [500, 5000],
        "help": "Lower = easier to interrupt (but might trigger from speaker). Higher = need to speak louder."
    },
    "energy_threshold": {
        "value": 300,
        "description": "Minimum mic energy to detect speech",
        "range": [100, 1000],
        "help": "Lower = more sensitive (picks up quiet speech). Higher = ignores background noise."
    },

    # Personality
    "user_name": {
        "value": "sir",
        "description": "What JARVIS calls you",
        "help": "Your name or a title. JARVIS will use this in conversation."
    },
    "personality": {
        "value": "default",
        "description": "JARVIS personality style",
        "options": ["default", "formal", "casual", "sarcastic"],
        "help": "default = MCU JARVIS, formal = more butler-like, casual = friendlier, sarcastic = more dry wit"
    },
    "response_length": {
        "value": "short",
        "description": "How long JARVIS responses are",
        "options": ["brief", "short", "medium"],
        "help": "brief = 1 sentence, short = 1-2 sentences, medium = 2-3 sentences"
    },
    "startup_greeting": {
        "value": True,
        "description": "JARVIS speaks when launched",
        "help": "Turn off if you don't want JARVIS to talk on startup."
    },

    # Features
    "enable_spotify": {
        "value": True,
        "description": "Spotify music control",
        "help": "Requires Spotify installed on your computer."
    },
    "enable_focus_mode": {
        "value": True,
        "description": "Focus mode / Pomodoro timer",
        "help": "Closes distracting apps and sets a work timer."
    },
    "enable_screen_capture": {
        "value": True,
        "description": "Screen capture & homework helper",
        "help": "Takes screenshots and analyzes them with AI vision."
    },
    "enable_file_finder": {
        "value": True,
        "description": "File search in Downloads/Documents/Desktop",
        "help": "Lets JARVIS find files on your computer."
    },
    "enable_easter_eggs": {
        "value": True,
        "description": "Easter egg responses",
        "help": "Fun hidden responses to things like 'I am Iron Man'."
    },

    # Audio
    "chime_volume": {
        "value": 0.25,
        "description": "Volume of activation/notification sounds",
        "range": [0.0, 1.0],
        "help": "0.0 = silent, 0.25 = default, 1.0 = max"
    },
    "tts_voice_id": {
        "value": "612b878b113047d9a770c069c8b4fdfe",
        "description": "Fish Audio voice model ID",
        "help": "Default is MCU JARVIS. Browse voices at fish.audio to find others."
    },
}


def load_settings() -> dict:
    """Load settings from file, falling back to defaults."""
    settings = {k: v["value"] for k, v in DEFAULTS.items()}

    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r') as f:
                saved = json.load(f)
            settings.update(saved)
        except:
            pass

    # Also pull user_name from .env if not set in settings
    if settings["user_name"] == "sir":
        from dotenv import load_dotenv
        load_dotenv()
        env_name = os.getenv("USER_NAME", "sir")
        if env_name != "sir":
            settings["user_name"] = env_name

    return settings


def save_settings(settings: dict):
    """Save settings to file."""
    with open(SETTINGS_FILE, 'w') as f:
        json.dump(settings, f, indent=2)
    print(f"\nSettings saved to {SETTINGS_FILE}")


def print_settings(settings: dict):
    """Display current settings."""
    print("\n  Current Settings:")
    print("  " + "─" * 50)

    categories = {
        "Voice & Listening": ["whisper_model", "silence_seconds", "conversation_timeout",
                              "interrupt_threshold", "energy_threshold"],
        "Personality": ["user_name", "personality", "response_length", "startup_greeting"],
        "Features": ["enable_spotify", "enable_focus_mode", "enable_screen_capture",
                      "enable_file_finder", "enable_easter_eggs"],
        "Audio": ["chime_volume", "tts_voice_id"],
    }

    for cat_name, keys in categories.items():
        print(f"\n  {cat_name}:")
        for key in keys:
            desc = DEFAULTS[key]["description"]
            val = settings.get(key, DEFAULTS[key]["value"])
            print(f"    {desc}: {val}")


def interactive_setup():
    """Interactive settings wizard."""
    settings = load_settings()

    print("\n══════════════════════════════════════════════════")
    print("  J.A.R.V.I.S. — Settings")
    print("══════════════════════════════════════════════════")
    print_settings(settings)

    while True:
        print("\n  Options:")
        print("    1. Quick setup (recommended for first time)")
        print("    2. Change a specific setting")
        print("    3. Reset to defaults")
        print("    4. Save and exit")
        print("    5. Exit without saving")

        choice = input("\n  Choose (1-5): ").strip()

        if choice == "1":
            settings = quick_setup(settings)
        elif choice == "2":
            settings = change_setting(settings)
        elif choice == "3":
            settings = {k: v["value"] for k, v in DEFAULTS.items()}
            print("\n  Reset to defaults.")
            print_settings(settings)
        elif choice == "4":
            save_settings(settings)
            break
        elif choice == "5":
            print("\n  Exiting without saving.")
            break


def quick_setup(settings: dict) -> dict:
    """Guided quick setup for new users."""
    print("\n  Quick Setup")
    print("  " + "─" * 40)

    # Name
    name = input(f"\n  What should JARVIS call you? [{settings['user_name']}]: ").strip()
    if name:
        settings["user_name"] = name

    # Whisper model
    print(f"\n  Speech recognition speed:")
    print("    1. Fast (less accurate, good for simple commands)")
    print("    2. Balanced (recommended)")
    print("    3. Accurate (slower, better for complex speech)")
    model_choice = input("  Choose [2]: ").strip() or "2"
    settings["whisper_model"] = {"1": "tiny.en", "2": "base.en", "3": "small.en"}.get(model_choice, "base.en")

    # Personality
    print(f"\n  JARVIS personality:")
    print("    1. Classic MCU JARVIS (recommended)")
    print("    2. More formal / butler-like")
    print("    3. Casual and friendly")
    print("    4. Extra sarcastic")
    pers_choice = input("  Choose [1]: ").strip() or "1"
    settings["personality"] = {"1": "default", "2": "formal", "3": "casual", "4": "sarcastic"}.get(pers_choice, "default")

    # Response length
    print(f"\n  Response length:")
    print("    1. Brief (1 sentence)")
    print("    2. Short (1-2 sentences, recommended)")
    print("    3. Medium (2-3 sentences)")
    len_choice = input("  Choose [2]: ").strip() or "2"
    settings["response_length"] = {"1": "brief", "2": "short", "3": "medium"}.get(len_choice, "short")

    # Startup greeting
    greet = input(f"\n  JARVIS speaks on startup? (y/n) [{('y' if settings['startup_greeting'] else 'n')}]: ").strip().lower()
    if greet in ('y', 'n'):
        settings["startup_greeting"] = greet == 'y'

    print_settings(settings)
    return settings


def change_setting(settings: dict) -> dict:
    """Change a specific setting."""
    all_keys = list(DEFAULTS.keys())

    print("\n  Available settings:")
    for i, key in enumerate(all_keys, 1):
        desc = DEFAULTS[key]["description"]
        val = settings.get(key, DEFAULTS[key]["value"])
        print(f"    {i}. {desc} = {val}")

    try:
        idx = int(input("\n  Setting number: ").strip()) - 1
        key = all_keys[idx]
    except (ValueError, IndexError):
        print("  Invalid choice.")
        return settings

    info = DEFAULTS[key]
    print(f"\n  {info['description']}")
    print(f"  Current: {settings.get(key, info['value'])}")
    print(f"  Help: {info['help']}")

    if "options" in info:
        print(f"  Options: {', '.join(str(o) for o in info['options'])}")
        new_val = input(f"  New value: ").strip()
        if new_val in [str(o) for o in info["options"]]:
            settings[key] = new_val
        else:
            print("  Invalid option.")
    elif "range" in info:
        print(f"  Range: {info['range'][0]} to {info['range'][1]}")
        try:
            new_val = float(input(f"  New value: ").strip())
            if info['range'][0] <= new_val <= info['range'][1]:
                settings[key] = int(new_val) if isinstance(info['value'], int) else new_val
            else:
                print("  Out of range.")
        except ValueError:
            print("  Invalid number.")
    elif isinstance(info['value'], bool):
        new_val = input(f"  Enable? (y/n): ").strip().lower()
        if new_val in ('y', 'n'):
            settings[key] = new_val == 'y'
    else:
        new_val = input(f"  New value: ").strip()
        if new_val:
            settings[key] = new_val

    print(f"  Updated: {info['description']} = {settings[key]}")
    return settings


if __name__ == "__main__":
    interactive_setup()
