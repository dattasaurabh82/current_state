# World Theme Music Player

[![License: Unlicense](https://img.shields.io/badge/license-Unlicense-blue.svg)](LICENSE)
[![Platform: Raspberry Pi](https://img.shields.io/badge/platform-Raspberry%20Pi-c51a4a.svg)](https://www.raspberrypi.org/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

> **An AI-powered ambient music generator that transforms daily world news into mood-based soundscapes. Designed to sit on top of IKEA FREKVANS SPEAKERS, this will trigger playback of AI generated soundscape/music when a person enters a room or a motion is detected. So a suitable place for this are contemplation rooms like bathrooms 🙃**

![alt text](assets/current_state_header_img.001.png)

*How does it look like?*

![Web Dashboard Preview](assets/web-monitor-preview-2.png) 

*Monitor Web Dashboard*

The main functionality of the system is to system fetch news headlines from multiple regions, analyzes their emotional tone using an LLM, selects musical archetypes, and generates unique ambient music — all running autonomously on a Raspberry Pi and using open-source local LLM models hosted on [Replicate](https://replicate.com/). 
With onboard hardware buttons, all functionalities can be triggered and controlled. For example,  disabling radar trigger or shutting down or turning ON the PI or even resetting WiFi for the PI, can all be carried out via the custom PI HAT I designed! (More on that later ...) 

---

## Table of Contents

- [How It Works](#how-it-works)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration Reference](#configuration-reference)
- [WiFi Manager](#wifi-manager)
- [Hardware Testing](#hardware-testing)
- [Services Installation](#services-installation)
- [Web Dashboard](#web-dashboard)
- [Hardware Setup](#hardware-setup)
- [Project Structure](#project-structure)
- [License](#license)
- [TODO](#todo)

---

## How It Works

The system has two modes of operation:

![alt text](<assets/How It Works.png>)

### Pipeline Overview

The **automated pipeline** runs daily at 3:00 AM:

> [!Note]
> This 3:00 AM is defined in cronjob settings which can be manually altered but it is defined in the [services/01_install_and_start_services.sh](services/01_install_and_start_services.sh)

| Stage | What Happens |
|-------|--------------|
| **Fetch** | NewsAPI provides headlines in 4 languages (EN, DE, FR, ES) — 4 API requests total |
| **Analyze** | Llama 3 70B extracts mood: valence (-1 to +1), tension (0-1), hope (0-1), energy level |
| **Select** | Rule-based scoring matches the mood profile to one of 6 musical archetypes |
| **Build** | Three-layer prompt construction: archetype structure + theme textures + daily variety |
| **Generate** | MusicGen stereo-melody-large creates a 30-second ambient piece |
| **Process** | Fade-in (1.5s) and fade-out (2s) are applied |

The **user-triggered interactions** happen via hardware:

| Trigger | Action |
|---------|--------|
| **GPIO17 Button** | Manually triggers the full news→music pipeline |
| **Radar Motion** | Starts looping playback when presence is detected (see [Radar Behavior](#radar-behavior)) |
| **Radar Enable Switch** | GPIO6 toggle — when ON, radar controls playback; when OFF, radar is ignored |
| **Play/Pause Button** | Toggle playback state |
| **Stop Button** | Stop playback completely |

---

## Prerequisites

### Hardware

![alt text](assets/curr_state.gif)

> [!NOTE]
> Hardware details TBD — Custom HAT design documentation coming soon.

TODO: Add hardware list, circuit diagram, etc.

---

### API Accounts

Before running the setup script, create accounts and gather these credentials:

| Service | What You Need | Where to Get It |
|---------|---------------|-----------------|
| **NewsAPI** | API Key | [newsapi.org/account](https://newsapi.org/account) → Generate API Key |
| **Replicate** | API Token | [replicate.com/account/api-tokens](https://replicate.com/account/api-tokens) |

> [!TIP]
> **Keep these credentials handy** — you'll need them when running `setup.sh` in the next section.

#### Cost Breakdown

| Service | Plan | Usage | Cost |
|---------|------|-------|------|
| **NewsAPI** | Free tier (100 requests/day) | 4 requests/day (one per language) | **Free** |
| **Replicate** | Pay-per-use | ~1 generation/day | **~$0.30/month** |

**Replicate cost details:**
- MusicGen runs on Nvidia A100 (80GB) @ $0.00140/sec — typical generation takes ~50-60 seconds = ~$0.07-0.08
- Llama 3 70B runs on Nvidia A100 (80GB) @ $0.00140/sec — typical analysis takes ~10-15 seconds = ~$0.01-0.02
- **Total per generation: ~$0.08-0.10**

**NewsAPI notes:**
- Uses the `/everything` endpoint to fetch recent articles
- Free tier provides access to articles from the previous day
- Our system makes only 4 requests daily (one per language: EN, DE, FR, ES), well under the 100/day limit

---

## Installation

### Step 1: Set Pi Date/Time

First, verify your Pi's date is correct:

```bash
date
```

If incorrect, fix via `raspi-config`:

```bash
sudo raspi-config
```

| Step | View |
|------|------|
| Select "Localisation Options" → ENTER | ![raspi-config step 1](assets/rpi-config-date-1.png) |
| Select "Timezone" → ENTER | ![raspi-config step 2](assets/rpi-config-date-2.png) |
| Select your region | ![raspi-config step 3](assets/rpi-config-date-3.png) |

Tab to `<Finish>` and reboot:

```bash
sudo reboot
```

### Step 2: Run Setup Script

> [!NOTE]
> **TBD** — Automated setup script coming soon.
> 
> The script will:
> - Install system dependencies (build tools, audio libs)
> - Install UV package manager
> - Clone the repository
> - Create virtual environment
> - Prompt for API credentials and create `.env`
> - Configure GPIO permissions

For now, see [Manual Setup Instructions](#manual-setup-instructions) at the bottom.

---

## Configuration Reference

Before testing hardware, familiarize yourself with the configuration files.

### `settings.json`

Controls GPIO pins, hardware behavior, and feature settings:

```json
{
  "inputPins": {
    "playPauseBtnPin": 22,
    "stopBtnPin": 27,
    "runFullCycleBtnPin": 17,
    "radarEnablePin": 6,
    "radarModel": "RCWL-0516",
    "radarPin": 16
  },
  "outputPins": {
    "playerStateLEDPin": 25,
    "radarStateLEDPin": 23
  },
  "hwFeatures": {
    "btnDebounceTimeMs": 0.05,
    "maxLEDBrightness": 25,
    "pauseBreathingFreq": 0.25,
    "motionTriggeredPlaybackDurationSec": 300,
    "cooldownAfterUserActionSec": 60,
    "radarMaxRangeMeters": 2.5,
    "radarTargetTimeoutSec": 1.0
  },
  "music": {
    "fadeInDurationSec": 1.5,
    "fadeOutDurationSec": 2.0
  }
}
```

#### Key Settings Explained

| Setting | Default | Description |
|---------|---------|-------------|
| `radarEnablePin` | 6 | GPIO pin for radar enable switch — when HIGH, radar triggers playback |
| `radarModel` | `RCWL-0516` | Radar type: `RCWL-0516` (GPIO) or `RD-03D` (Serial UART) |
| `motionTriggeredPlaybackDurationSec` | 300 | How long music plays after motion detected (5 minutes) |
| `cooldownAfterUserActionSec` | 60 | After user presses pause/stop, radar is ignored for this duration |
| `radarMaxRangeMeters` | 2.5 | Detection range (RD-03D only) |
| `maxLEDBrightness` | 25 | LED brightness (0-100) |

### `news_config.json`

Configures which language regions to fetch news from:

```json
{
  "regions": {
    "English_Speaking": { "language": "en" },
    "German_Speaking": { "language": "de" },
    "French_Speaking": { "language": "fr" },
    "Spanish_Speaking": { "language": "es" }
  }
}
```

### `.env`

API credentials (created from `.env.template`):

```bash
NEWS_API_KEY="your_newsapi_key"
REPLICATE_API_TOKEN="your_replicate_token"
```

---

## WiFi Manager

For headless WiFi configuration without monitor/keyboard, install the [rpi-wifi-configurator](https://github.com/dattasaurabh82/rpi-wifi-configurator) project.

> [!IMPORTANT]
> Install WiFi Manager **before** hardware testing. The service uses GPIO 23 (shared with Radar LED), so you'll need to stop it temporarily during button/LED tests.

### How It Works

1. **Long press** the WiFi reset button (>4 sec)
2. Pi creates an Access Point (`RPI_NET_SETUP`)
3. Connect your phone/laptop to that AP
4. Navigate to `http://10.10.1.1:4000`
5. Enter your WiFi SSID and password
6. Pi connects to your network

### Installation

```bash
curl -fsSL https://raw.githubusercontent.com/dattasaurabh82/rpi-wifi-configurator/main/install.sh | bash
```

During setup, enter these GPIO settings for this project:

| Setting | Value | Notes |
|---------|-------|-------|
| Button GPIO | **26** | `NET_RESET_BTN` — dedicated WiFi reset button |
| LED GPIO | **23** | Shared with Radar LED |

### LED Status Indicators

| LED State | Pattern | Meaning |
|-----------|---------|---------|
| **OFF** | No light | Connected to WiFi (normal operation) |
| **SLOW BREATH** | Smooth pulse | Searching for WiFi / attempting connection |
| **FAST BLINK** | Quick on/off | AP mode active (ready for configuration) |
| **SOLID → OFF** | 2 sec solid | Connection successful |

### Stopping for Hardware Tests

Before running hardware tests, stop the WiFi manager service to free up GPIO 23:

```bash
sudo systemctl stop rpi-btn-wifi-manager.service
```

After testing, restart it:

```bash
sudo systemctl start rpi-btn-wifi-manager.service
```

---

## Hardware Testing

Before installing services, test each component individually to verify wiring and configuration.

> [!NOTE]
> If you installed the WiFi Manager, **stop it first** before testing buttons and LEDs:
> ```bash
> sudo systemctl stop rpi-btn-wifi-manager.service
> ```

### Test GPIO Buttons & LEDs

```bash
uv run python tests/01_test_IOs.py
```

**What to expect:**
- Press each button and observe console output confirming the press
- LEDs should light up when tested

**Pins being tested:**

| Component | GPIO |
|-----------|------|
| Play/Pause Button | 22 |
| Stop Button | 27 |
| Full Cycle Button | 17 |
| Radar Enable Switch | 6 |
| Player State LED | 25 |
| Radar State LED | 23 |

### Test Radar Detection

The radar sensor enables automatic, presence-triggered playback. This is useful for installation scenarios where you want music to play when someone approaches.

#### Radar Behavior

When the **Radar Enable Switch** (GPIO 6) is ON:

1. **Motion detected** → Music starts playing in a loop
2. **Music plays for 5 minutes** (configurable: `motionTriggeredPlaybackDurationSec`)
3. **No motion for 5 min** → Music auto-stops
4. **Motion detected again** → Playback resumes

**Cooldown behavior:** If a user manually presses **Pause** or **Stop**, the radar is temporarily ignored for 60 seconds (configurable: `cooldownAfterUserActionSec`). This prevents the radar from immediately restarting playback after a deliberate user action.

#### Radar Models

| Radar Model | Interface | Best For |
|-------------|-----------|----------|
| `RCWL-0516` | GPIO (digital HIGH/LOW) | Simple presence detection |
| `RD-03D` | Serial (UART) | Distance-based detection with configurable range |

Ensure your radar model is set in `settings.json`:

```json
{
  "inputPins": {
    "radarModel": "RCWL-0516",
    "radarPin": 16,
    "radarEnablePin": 6
  }
}
```

Run the appropriate test:

```bash
# For RCWL-0516 (GPIO-based)
uv run python tests/02_test_event_radar.py

# For RD-03D (Serial-based)
uv run python tests/02_test_serial_radar.py
```

**What to expect:**
- Walk in front of the sensor
- Console shows "Motion detected" / "Motion stopped"
- Radar LED (GPIO 23) lights up during detection

### Test Audio Output

Verify the speaker/audio output is working:

```bash
aplay keep_audio_ch_active.wav
```

**What to expect:** You should hear a short tone.

### Test Full Pipeline

Generate music without playback to verify API connectivity:

```bash
uv run python main.py --fetch true --play false
```

**What to expect:**
- News headlines are fetched and cached to `news_data_YYYY-MM-DD.json`
- LLM analyzes mood (takes ~10-20 seconds)
- MusicGen generates audio (takes ~50-60 seconds)
- Output saved to `music_generated/world_theme_YYYY-MM-DD_HH-MM-SS.wav`

### Test Hardware Player

Interactive test with keyboard controls:

```bash
uv run python run_player.py
```

**Controls:**

| Key | Action |
|-----|--------|
| `P` | Play / Pause |
| `S` | Stop |
| `Q` | Quit |

**What to expect:**
- Player finds the latest song in `music_generated/`
- Press `P` to play — LED goes solid
- Press `P` again to pause — LED breathes
- Press `S` to stop — LED turns off

For daemon mode (no keyboard, GPIO buttons only):

```bash
uv run python run_player.py --daemon
```

### Re-enable WiFi Manager

After testing, restart the WiFi manager if you installed it:

```bash
sudo systemctl start rpi-btn-wifi-manager.service
```

---

## Services Installation

Once hardware testing passes, install the background services.

### Check Current Status

```bash
./services/00_status.sh
```

### Install All Services

```bash
./services/01_install_and_start_services.sh
```

**This installs:**

| Service | Description |
|---------|-------------|
| `music-player.service` | Plays music, handles GPIO buttons, radar detection |
| `full-cycle-btn.service` | GPIO17 button triggers full news→music pipeline |
| `process-monitor-web.service` | Web dashboard on port 7070 |
| nginx | Reverse proxy (access dashboard on port 80) |

### Verify Installation

```bash
./services/00_status.sh
```

**Expected output:**

```
User Services

  ● full-cycle-btn.service
  ● music-player.service
  ● process-monitor-web.service

nginx

  ● nginx
  ● config installed
```

### Uninstall Services

```bash
./services/04_stop_and_uninstall_services.sh
```

### Useful Commands

```bash
# Check individual service
systemctl --user status music-player.service

# Follow logs in real-time
journalctl --user -u music-player.service -f

# Manually trigger generation
uv run python main.py --fetch true --play false
```

---

## Web Dashboard

A TUI-style web interface for monitoring the pipeline from any device on your network.

![Web Dashboard](assets/web-monitor-preview-2.png)

### Features

| Tab | Description |
|-----|-------------|
| **News** | Today's headlines grouped by region (from cached JSON) |
| **Pipeline** | Interactive graph: mood analysis → archetypes → prompt components |
| **Logs** | Live streaming logs (like `tail -f` in your browser) |

### Access URLs

| Method | URL |
|--------|-----|
| Via nginx | `http://aimusicplayer.local` |
| Direct | `http://aimusicplayer.local:7070` |

### Where to Find Things

| What | Location |
|------|----------|
| Generated music | `music_generated/` |
| Today's news | `news_data_YYYY-MM-DD.json` |
| Pipeline results | `generation_results/pipeline_results.json` |
| Visualizations | `generation_results/visualizations/` |
| Logs | `logs/` |

📖 **Full documentation:** [`web/README.md`](web/README.md)

---

## Hardware Setup

### Shutdown & Wake Button (GPIO3)

Enable hardware shutdown/wake using a dedicated button on GPIO3.

#### Step 1: Disable I2C

> [!WARNING]
> GPIO3 is shared with I2C SCL. You must disable I2C to use it for shutdown.

```bash
sudo raspi-config
```

| Step | View |
|------|------|
| Select *Interface Options* | ![Step 1](assets/disableI2c_step1.png) |
| Select *I2C* | ![Step 2](assets/disableI2c_step2.png) |
| Select *No* to disable | ![Step 3](assets/disableI2c_step3.png) |
| *Finish* and reboot | ![Step 4](assets/disableI2c_step4.png) |

#### Step 2: Enable gpio-shutdown Overlay

```bash
sudo nano /boot/firmware/config.txt
```

Add after the overlays comment section:

```ini
dtoverlay=gpio-shutdown
```

Reboot and test:
- Press GPIO3 button → Pi shuts down
- Press again → Pi wakes up

---

## Project Structure

```txt
├── README.md
├── LICENSE
├── pyproject.toml
├── uv.lock
├── main.py                      # Pipeline orchestrator
├── run_player.py                # Hardware player daemon
├── run_full_cycle_btn.py        # GPIO17 button handler
├── keep_audio_ch_active.wav     # Speaker keep-alive tone
├── settings.json                # Hardware & feature config
├── news_config.json             # News regions config
├── .env                         # API credentials (create from template)
│
├── lib/                         # Core modules
│   ├── news_fetcher.py          # NewsAPI client
│   ├── llm_analyzer.py          # LLM mood extraction
│   ├── archetype_selector.py    # Rule-based archetype scoring
│   ├── music_prompt_builder.py  # 3-layer prompt construction
│   ├── music_generator.py       # MusicGen via Replicate
│   ├── music_post_processor.py  # Fade in/out
│   ├── player.py                # Audio playback engine
│   ├── hardware_player.py       # GPIO buttons, LEDs, radar
│   ├── radar_controller.py      # RCWL-0516 / RD-03D support
│   └── settings.py              # Settings loader
│
├── services/                    # Systemd service management
│   ├── 00_status.sh             # Check all services
│   ├── 01_install_and_start_services.sh
│   ├── 04_stop_and_uninstall_services.sh
│   └── *.service                # Service unit files
│
├── web/                         # Dashboard (FastAPI + WebSocket)
├── tests/                       # Hardware test scripts
├── tools/                       # Utilities
├── logs/                        # Runtime logs
├── music_generated/             # Output audio files
├── generation_results/          # Pipeline outputs + visualizations
└── assets/                      # Documentation images
```

---

## License

[Unlicense](LICENSE)

---

## Manual Setup Instructions

<details>
<summary><strong>Click to expand</strong> — Reference for setup.sh development</summary>

### Install System Dependencies

```bash
sudo apt update -y
sudo apt upgrade -y 
sudo apt install git -y 
sudo apt install build-essential libssl-dev zlib1g-dev libbz2-dev libreadline-dev libsqlite3-dev curl libncursesw5-dev xz-utils tk-dev libxml2-dev libxmlsec1-dev libffi-dev liblzma-dev jq tree -y
sudo apt install python3-dev -y
```

### Install Audio Dependencies

```bash
sudo apt-get install libportaudio2 -y
```

### Install UV

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### GPIO Permissions

```bash
sudo usermod -a -G gpio $USER
sudo reboot
```

### Clone & Install

```bash
git clone https://github.com/YOUR_USERNAME/current_state.git
cd current_state
uv sync
```

If RPi.GPIO fails:
```bash
uv pip install RPi.GPIO --break-system-packages
```

### Create Environment File

```bash
cp .env.template .env
nano .env
```

Add your credentials:
```bash
NEWS_API_KEY="your_newsapi_key"
REPLICATE_API_TOKEN="your_replicate_token"
```

### Manual Service Installation (Legacy)

If not using the install script:

```bash
# Create user systemd directory
mkdir -p ~/.config/systemd/user

# Music Player
cp services/music-player.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now music-player.service

# Full Cycle Button
cp services/full-cycle-btn.service ~/.config/systemd/user/
systemctl --user enable --now full-cycle-btn.service

# Enable linger (services run without login)
sudo loginctl enable-linger $USER
```

</details>

---

## TODO

- WIP: Main README Docu ... 🟠
- Canvas to show in tablet landscape mode ...
- Serial Radar detection algo improve (beam and enter and exit based)
- Setup scripts:
  - Main dep install scripts
- Other region of news

- Hardware Update Steps: 
  - Speaker Switch switcher 
  - Update circuit 
    - Also add an extra (3D) side Fan for PI
  - Place new order for SLA prints 
  - Print PLA locally 
  - Assemble new one ... 

**Future**:
- More archetypes
- Embedding models if needed
- Data viz after a period of time on the world sentiment shifts
