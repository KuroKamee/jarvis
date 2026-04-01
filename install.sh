#!/bin/bash
# ══════════════════════════════════════════════════════
#  J.A.R.V.I.S. — Auto Installer
#  Run: bash install.sh
# ══════════════════════════════════════════════════════

set -e
clear

echo "══════════════════════════════════════════════════"
echo "  J.A.R.V.I.S. — Installer"
echo "══════════════════════════════════════════════════"
echo ""

# ── Detect OS ─────────────────────────────────────────
OS="unknown"
if [[ "$OSTYPE" == "darwin"* ]]; then
    OS="mac"
    echo "  Detected: macOS"
elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" || "$OSTYPE" == "cygwin" ]]; then
    OS="windows"
    echo "  Detected: Windows"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="linux"
    echo "  Detected: Linux"
fi
echo ""

# ── Check Python ──────────────────────────────────────
echo "[1/6] Checking Python..."

PYTHON_CMD=""
for cmd in python3.12 python3.11 python3.10 python3; do
    if command -v $cmd &> /dev/null; then
        version=$($cmd --version 2>&1 | grep -oP '\d+\.\d+')
        major=$(echo $version | cut -d. -f1)
        minor=$(echo $version | cut -d. -f2)
        if [[ "$major" -eq 3 && "$minor" -ge 10 && "$minor" -le 12 ]]; then
            PYTHON_CMD=$cmd
            echo "  Found: $($cmd --version)"
            break
        fi
    fi
done

if [[ -z "$PYTHON_CMD" ]]; then
    echo "  Python 3.10-3.12 not found."
    if [[ "$OS" == "mac" ]]; then
        echo "  Installing Python 3.12 via Homebrew..."
        if ! command -v brew &> /dev/null; then
            echo "  Installing Homebrew first..."
            /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        fi
        brew install python@3.12
        PYTHON_CMD="python3.12"
    elif [[ "$OS" == "windows" ]]; then
        echo "  Please install Python 3.12 from python.org"
        echo "  IMPORTANT: Check 'Add Python to PATH' during install!"
        exit 1
    elif [[ "$OS" == "linux" ]]; then
        echo "  Installing Python 3.12..."
        sudo apt update && sudo apt install -y python3.12 python3.12-venv
        PYTHON_CMD="python3.12"
    fi
fi

# ── Check ffmpeg ──────────────────────────────────────
echo ""
echo "[2/6] Checking ffmpeg..."

if command -v ffmpeg &> /dev/null; then
    echo "  Found: $(ffmpeg -version 2>&1 | head -1)"
else
    echo "  Installing ffmpeg..."
    if [[ "$OS" == "mac" ]]; then
        brew install ffmpeg
    elif [[ "$OS" == "linux" ]]; then
        sudo apt install -y ffmpeg
    elif [[ "$OS" == "windows" ]]; then
        echo "  Please install ffmpeg: winget install ffmpeg"
        exit 1
    fi
fi

# ── Check portaudio (Mac) ────────────────────────────
if [[ "$OS" == "mac" ]]; then
    echo ""
    echo "[2.5/6] Checking portaudio..."
    if brew list portaudio &> /dev/null 2>&1; then
        echo "  Found portaudio."
    else
        echo "  Installing portaudio..."
        brew install portaudio
    fi
fi

# ── Create venv ───────────────────────────────────────
echo ""
echo "[3/6] Creating virtual environment..."

if [[ -d "venv" ]]; then
    echo "  Existing venv found. Removing..."
    rm -rf venv
fi

$PYTHON_CMD -m venv venv

if [[ "$OS" == "windows" ]]; then
    source venv/Scripts/activate
else
    source venv/bin/activate
fi
echo "  Virtual environment created."

# ── Install packages ──────────────────────────────────
echo ""
echo "[4/6] Installing Python packages (this takes a minute)..."
pip install --upgrade pip -q
pip install -r requirements.txt -q
echo "  All packages installed."

# ── Download wake word model ──────────────────────────
echo ""
echo "[5/6] Downloading wake word model..."
python -c "from openwakeword import utils; utils.download_models()" 2>/dev/null
echo "  Wake word model ready."

# ── Setup API keys ────────────────────────────────────
echo ""
echo "[6/6] Setting up configuration..."

if [[ -f ".env" ]]; then
    echo "  Existing .env found. Keeping it."
else
    echo ""
    echo "  You need two API keys to run JARVIS:"
    echo ""
    echo "  1. Anthropic API key (for the AI brain)"
    echo "     Get one at: https://console.anthropic.com"
    echo "     Cost: ~\$1-3/month for casual use"
    echo ""
    echo "  2. Fish Audio API key (for the JARVIS voice)"
    echo "     Get one at: https://fish.audio"
    echo "     Cost: Free tier available"
    echo ""

    read -p "  Enter your Anthropic API key (or press Enter to skip): " ANTHROPIC_KEY
    read -p "  Enter your Fish Audio API key (or press Enter to skip): " FISH_KEY
    read -p "  Enter your name (JARVIS will use it): " USER_NAME

    if [[ -z "$USER_NAME" ]]; then
        USER_NAME="sir"
    fi

    cat > .env << EOF
ANTHROPIC_API_KEY=${ANTHROPIC_KEY:-your-anthropic-api-key-here}
FISH_API_KEY=${FISH_KEY:-your-fish-audio-api-key-here}
USER_NAME=${USER_NAME}
EOF

    echo "  Configuration saved to .env"

    if [[ -z "$ANTHROPIC_KEY" || -z "$FISH_KEY" ]]; then
        echo ""
        echo "  ⚠ You skipped one or both API keys."
        echo "  Edit .env before running JARVIS:"
        if [[ "$OS" == "windows" ]]; then
            echo "    notepad .env"
        else
            echo "    nano .env"
        fi
    fi
fi

# ── Run settings wizard ──────────────────────────────
echo ""
read -p "  Would you like to customize JARVIS settings? (y/n): " CUSTOMIZE

if [[ "$CUSTOMIZE" == "y" || "$CUSTOMIZE" == "Y" ]]; then
    python settings.py
fi

# ── Done ──────────────────────────────────────────────
echo ""
echo "══════════════════════════════════════════════════"
echo "  Installation complete!"
echo ""
echo "  To start JARVIS:"
if [[ "$OS" == "mac" ]]; then
    echo "    Double-click start_jarvis.command"
    echo "    Or run: python3 voice_assistant.py"
elif [[ "$OS" == "windows" ]]; then
    echo "    Double-click start_jarvis.bat"
    echo "    Or run: python voice_assistant.py"
else
    echo "    Run: python3 voice_assistant.py"
fi
echo ""
echo "  Say \"Hey JARVIS\" to activate."
echo "══════════════════════════════════════════════════"
