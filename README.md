# JARVIS (first release, this took awhile)

A voice assistant that runs on your computer. Say "Hey JARVIS" and talk to it — it talks back in the MCU JARVIS voice. Built with Python, works on Mac and Windows, costs a few bucks a month.

## Demo

*(Will add soon)*

## Why I Built This

I wanted a voice assistant similar to the one seen in Marvels, Ironman. I looked for existing projects however, it seems most of them are built on exspensive API's or just isn't compatible with lower-tier devices. So I rebuilt the concept from scratch — cross-platform, modular, and cheap to run. The only paid services are Claude Haiku (~$1-3/mo) for intelligence and Fish Audio (free tier) for the voice.

Everything else runs locally: speech recognition, wake word detection, timers, notes, search, math — all free.

## Getting Started

You'll need API keys from two services:

| Service | Purpose | Get it at | Cost |
|---------|---------|-----------|------|
| Anthropic | AI brain | [console.anthropic.com](https://console.anthropic.com) | ~$1-3/mo |
| Fish Audio | JARVIS voice | [fish.audio](https://fish.audio) | Free tier |

Then install:

```bash
git clone https://github.com/KuroKamee/jarvis.git
cd jarvis
bash install.sh
```

The installer detects your OS, installs what's missing, and walks you through pasting your API keys.

Or set up manually — expand below.

<details>
<summary><strong>Manual setup (Mac)</strong></summary>

```bash
brew install python@3.12 portaudio ffmpeg
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -c "from openwakeword import utils; utils.download_models()"
cp .env.example .env
nano .env   # paste your API keys
python voice_assistant.py
```
</details>

<details>
<summary><strong>Manual setup (Windows)</strong></summary>

Install Python 3.12 from [python.org](https://python.org) (check "Add to PATH") and ffmpeg via `winget install ffmpeg`, then:

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python -c "from openwakeword import utils; utils.download_models()"
copy .env.example .env
notepad .env   # paste your API keys
python voice_assistant.py
```
</details>

After the first setup, launch JARVIS by double-clicking `start_jarvis.command` (Mac) or `start_jarvis.bat` (Windows).

## Things You Can Say

Here are some examples. You don't need to memorize commands — just talk naturally and JARVIS figures out what you mean.

**Everyday stuff**
> "What time is it?" · "What's the weather?" · "Set a timer for 10 minutes" · "Brief me"

**Music**
> "Play Bohemian Rhapsody by Queen" · "Next track" · "What song is this?" · "Pause"

**Getting things done**
> "Focus mode for 25 minutes" · "Take a note: dentist on Friday" · "Read my notes" · "Find that PDF I downloaded"

**Thinking**
> "What's 20 percent of 347?" · "Convert 180 cm to feet" · "How long until 5pm?" · "Search for best mechanical keyboards"

**Screen + clipboard**
> "What's on my screen?" · "Help me with this problem" · "Read my clipboard" · "Rewrite my clipboard to sound professional"

**System**
> "Open Spotify" · "Close Discord" · "Turn up the volume" · "How's my system doing?"

**Just for fun**
> "Tell me a joke" · "Roast me" · "Quiz me on science" · "Flip a coin" · "Define serendipity" · "Translate thanks to Japanese"

There are also 20+ hidden easter eggs. Try "I am Iron Man" or "open the pod bay doors."

## Conversation Mode

After JARVIS responds, you have about 6 seconds to ask a follow-up without saying the wake word again. It feels like a real back-and-forth conversation.

You can also interrupt JARVIS mid-sentence by talking — it stops and listens to what you have to say.

Say "quiet mode" for text-only responses (no voice). Say "voice mode" to turn speech back on.

## Customization

Run the settings wizard:

```bash
python settings.py
```

Or edit `jarvis_settings.json` directly. You can adjust:

- Speech recognition speed vs accuracy
- How long JARVIS waits before it stops recording
- How sensitive the microphone is
- JARVIS personality (classic / formal / casual / sarcastic)
- Response length
- Which features are enabled
- Sound effect volume
- Voice model ID (swap to a different Fish Audio voice)

## Under the Hood

| File | Job |
|------|-----|
| `voice_assistant.py` | Runs the main loop: wake word → record → think → speak → repeat |
| `stt.py` | Converts your speech to text using Whisper (runs locally) |
| `llm.py` | Sends your request to Claude Haiku and gets a response |
| `tts.py` | Converts the response to the JARVIS voice via Fish Audio |
| `memory.py` | Remembers things you tell it using SQLite |
| `actions.py` | Opens apps, controls volume, sets timers, takes screenshots |
| `spotify.py` | Plays, pauses, skips music on Spotify |
| `search.py` | Searches the web (DuckDuckGo) and checks weather (wttr.in) |
| `tools.py` | Focus mode, notes, math, file search, trivia, easter eggs |
| `settings.py` | Interactive settings editor |

The flow is: openwakeword catches "Hey JARVIS" → Whisper transcribes what you say → simple stuff (time, math) is answered instantly without hitting the API → complex requests go to Claude Haiku → the LLM's response includes action tags that trigger real system actions → Fish Audio turns the response into speech → you hear JARVIS talk.

JARVIS auto-pauses Spotify when listening and resumes after responding. It auto-restarts if it crashes. It logs all conversations to `jarvis_log.json`. It warns you when battery is low.

## Running Costs

The only paid components are the AI brain and the voice. Everything else is free and local.

| What | How | Monthly |
|------|-----|---------|
| Speech recognition | Whisper (local) | $0 |
| Wake word | openwakeword (local) | $0 |
| Search + weather | DuckDuckGo + wttr.in | $0 |
| Notes, timers, math | Python | $0 |
| AI responses | Claude Haiku API | $1-3 |
| JARVIS voice | Fish Audio | $0-5.50 |

## Known Issues

- **Python 3.13+** doesn't work — onnxruntime hasn't caught up yet. Use 3.12.
- **Spotify play** uses web search to find track URLs. Occasionally picks the wrong result if the song name is generic.
- **Wake word** is "Hey JARVIS" not just "JARVIS" — openwakeword's closest built-in model.
- **Older Macs** (macOS 12 and below) compile some packages from source during install, which takes a while.

## Roadmap

Some things I want to add eventually:

- Google Calendar — "what's on my schedule?"
- Gmail summary — "any important emails?"
- Webpage summarizer — "summarize this link"
- Voice journal
- Smart home integration
- Custom wake word (just "JARVIS")
- Plugin system
- Multi-device (phone as remote mic)

## Contributing

PRs welcome. Good places to start:

- New easter eggs in `tools.py`
- More unit conversions in `tools.py`
- Windows app aliases in `actions.py`
- Better Spotify search in `spotify.py`
- Trivia questions in `tools.py`

Open an issue first for big changes so we can discuss.

## License

MIT — do whatever you want with it. See [LICENSE](LICENSE).

## Acknowledgments

Built with [Claude](https://anthropic.com) and [Fish Audio](https://fish.audio).

The JARVIS name belongs to Marvel Entertainment. This is a fan project.
