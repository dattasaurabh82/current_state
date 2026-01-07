# README

## ToDo

### Low

- WIP: Docu ...
- WIP: All code base cleanup - System provisioning docu and tooling ....
- maybe web ui
- SfX with music
- Other region of news 

### High

- Business logic of operation ... (radar trigger )
- Improve music prompt gen algo

### Backlog

- ~~How often and how long silent audio player plays~~
  - silent audio to keep the channel active did not work ... so implement HW sol to trigger Audio On on FREKVENS
- ~~Currently happy with the implementation~~
- ~~Send cancel to other agent calls~~
- ~~slow down track for 30 sec to make it feel longer [post processing]~~

---

## Project structure

```txt
├── assets
├── cron.log
├── Dockerfile
├── full_cycle_btn.log
├── full-cycle-btn.service
├── _HW
│   └── pi_hat
│       ├── bom
│       │   └── ibom.html
│       ├── GERBERS
│       │   ├── NEWS_POET_PI_HAT_PCB_v1_2025-11-17.zip
│       │   └── NEWS_POET_PI_HAT_PCB_V2_2025-12-04.zip
│       ├── NewsPoet.flbr
│       ├── NewsPoet.lbr
│       ├── PI_HAT.brd
│       ├── PI_HAT.f3d
│       ├── PI_HAT.f3z
│       ├── PI_HAT.fbrd
│       ├── PI_HAT.fsch
│       ├── PI_HAT_Fusion_Electronics_Design_Rule.dru
│       ├── PI_HAT_Fusion_Electronics_Design_Rule.edru
│       ├── PI_HAT.sch
│       └── references for silkscreen
│           ├── bottom.svg
│           ├── copper_bottom.gbr.svg
│           ├── copper_top.gbr.svg
│           ├── drill_1_64.xln.svg
│           ├── profile.gbr.svg
│           ├── README.md
│           ├── silkscreen_top.gbr.svg
│           ├── soldermask_bottom.gbr.svg
│           ├── soldermask_top.gbr.svg
│           ├── solderpaste_top.gbr.svg
│           ├── temp_outline.svg
│           └── top.svg
├── keep_audio_ch_active.wav
├── lib
│   ├── hardware_player.py
│   ├── __init__.py
│   ├── llm_analyzer.py
│   ├── music_generator.py
│   ├── music_post_processor.py
│   ├── news_fetcher.py
│   ├── player.py
│   ├── __pycache__
│   │   ├── hardware_player.cpython-311.pyc
│   │   ├── __init__.cpython-311.pyc
│   │   ├── llm_analyzer.cpython-311.pyc
│   │   ├── music_generator.cpython-311.pyc
│   │   ├── music_post_processor.cpython-311.pyc
│   │   ├── news_fetcher.cpython-311.pyc
│   │   ├── player.cpython-311.pyc
│   │   └── settings.cpython-311.pyc
│   └── settings.py
├── LICENSE
├── llm_agents
│   ├── __init__.py
│   ├── musicgen_prompt_crafter.py
│   ├── news_analyzer.py
│   └── __pycache__
│       ├── __init__.cpython-311.pyc
│       ├── musicgen_prompt_crafter.cpython-311.pyc
│       └── news_analyzer.cpython-311.pyc
├── main.py
├── music_created
├── music_generated
│   ├── generated_music_will_go_here
│   ├── world_theme_2025-10-01_01-01-51.wav
│   ├── world_theme_2025-10-02_01-01-30.wav
│   ├── world_theme_2025-10-03_01-01-37.wav
│   ├── world_theme_2025-10-04_01-01-29.wav
│   ├── world_theme_2025-10-05_01-01-24.wav
│   ├── world_theme_2025-10-06_01-02-13.wav
│   ├── world_theme_2025-10-07_01-01-28.wav
│   ├── world_theme_2025-10-08_01-01-39.wav
│   ├── world_theme_2025-10-10_01-02-01.wav
│   ├── world_theme_2025-10-11_01-01-32.wav
│   ├── world_theme_2025-10-12_01-01-51.wav
│   ├── world_theme_2025-10-13_01-01-50.wav
│   ├── world_theme_2025-10-14_01-01-41.wav
│   ├── world_theme_2025-10-15_01-01-36.wav
│   ├── world_theme_2025-10-16_01-02-39.wav
│   ├── world_theme_2025-10-19_01-01-36.wav
│   ├── world_theme_2025-10-20_01-03-02.wav
│   ├── world_theme_2025-11-20_02-01-19.wav
│   ├── world_theme_2026-01-07_00-46-31.wav
│   ├── world_theme_2026-01-07_01-09-00.wav
│   ├── world_theme_2026-01-07_01-10-14.wav
│   ├── world_theme_2026-01-07_01-18-28.wav
│   ├── world_theme_2026-01-07_01-23-39.wav
│   ├── world_theme_2026-01-07_01-49-57.wav
│   └── world_theme_2026-01-07_02-04-55.wav
├── music-player.service
├── news_config.json
├── news_data_2026-01-07.json
├── news_data_cache
├── PI-POSTBOOT-SETUP.md
├── player_service.log
├── prompts
│   ├── musicgen_prompt_crafter_system.md
│   └── news_analyzer_system.md
├── __pycache__
│   ├── emotion_analyzer.cpython-311.pyc
│   ├── llm_analyzer.cpython-311.pyc
│   ├── music_generator.cpython-311.pyc
│   ├── music_post_processor.cpython-311.pyc
│   ├── news_fetcher.cpython-311.pyc
│   └── player.cpython-311.pyc
├── pyproject.toml
├── README.md
├── run_full_cycle_btn.py
├── run_player.py
├── settings.json
├── tests
│   ├── 01_test_IOs.py
│   ├── 02_test_event_radar.py
│   ├── 02_test_serial_radar.py
│   └── __pycache__
│       └── test_replicate_musicgen.cpython-311.pyc
├── tools
│   ├── bkp_gen_music.py
│   └── helper_utils_will_go_here
├── uv.lock
└── world_theme_music_player.log
```

### Setup your pi time correct to region

First check your pi's current date and time 

```bash
date
```

If it is off, you can fix it via `raspi-config`

```bash
sudo raspi-config
```

| Steps | View |
| --- | --- |
| Select "Localisation Options" and hit ENTER | ![alt text](assets/rpi-config-date-1.png) |
| Select "Timezone" and hit ENTER | ![alt text](assets/rpi-config-date-2.png) |
| Select your region and follow the prompts | ![alt text](assets/rpi-config-date-3.png) |

Once happy, 'tab' to `<Finish>` and restart (`sudo reboot`)

---


### Install Python Build Dependencies:

```bash
sudo apt update -y
sudo apt upgrade -y 
sudo apt install git -y 
sudo apt install build-essential libssl-dev zlib1g-dev libbz2-dev libreadline-dev libsqlite3-dev curl libncursesw5-dev xz-utils tk-dev libxml2-dev libxmlsec1-dev libffi-dev liblzma-dev jq tree -y
sudo apt install python3-dev -y
```

### Install Audio deps

```bash
sudo apt-get install libportaudio2 -y
```

### Install UV

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Install docker

https://docs.docker.com/engine/install/raspberry-pi-os/


### Some permissions

```bash
sudo usermod -a -G gpio $USER
sudo reboot
```


## Project setup

1. git clone
2. uv sync
3. sometimes may need: `uv pip install RPi.GPIO` from project dir...

### Create necessary API keys and Access Tokens

```bash
cp .env.template .env
```

1. Update `NEWS_API_KEY`:
   1. It is used to fetch news from various regions of the world
   2. Create and account here: https://newsapi.org/account
   3. Then generate an API KEY
   4. Replace `"REPLACE_WITH_YOUR_NEWS_API_KEY_HERE_FROM"` with your NEW KEY. 
2. Update `REPLICATE_API_TOKEN`:
   1. We are using https://replicate.com/ to use a Open Source LLM (meta/meta-llama-3-70b-instruct) and an Open Source music gen model (meta/musicgen)
   2. Create and account here: https://replicate.com/account
   3. Setup billing here: https://replicate.com/account/billing (_Yes you would need a credit card but the cost is in pennies and the models only run once per day, once the system is setup and is up and running_)
   4. And generate an API KEY here: https://replicate.com/account/api-tokens
   5. Replace `"REPLACE_WITH_YOUR_REPLICATE_API_TOKEN_HERE"` with your NEW KEY. 
   6. (Optional) If you are curious, you can check out and test the models (for fun), from here (https://replicate.com/meta/meta-llama-3-70b-instruct) and here (https://replicate.com/meta/musicgen) 
3. Update `DROPBOX_ACCESS_TOKEN`:
   1. We use it to back up old gen music audio files. Of-course you would need a drop box account. Periodically old files are removed from disk to save space in the RPI. _If you want to manually do it and opt out from this dropbox matter, you can do so by following the instructions from [here](#gen-music-file-size-management)_
   2. Assuming you have a dropbox account, create a new empty folder in your dropbox's home directory and rename it to `currentStateMusicFilesBKP` (NAME MUST BE EXACT)
   3. Go to the [dev app console](https://www.dropbox.com/developers/apps?_tk=pilot_lp&_ad=topbar4&_camp=myapps) and create a new app called `currentStateMusicFilesBKP` (NAME MUST BE EXACT)
   4. Enable all permissions.
    ![alt text](assets/dropbox_permisions.png) 
   5. And settings should look like below. Under `OAuth 2`, hit the "Generate" button and copy the KEY. 
    ![alt text](assets/dropbox_settings.png)
   6. Replace the `"REPLACE_WITH_YOUR_DROPBOX_ACCESS_TOKEN_HERE"`, in the .env file, with your KEY. 


---

### Run tests

From `world_theme_music_player`, run:

```bash
uv run -m tests.test_analyzer
uv run -m tests.test_grab_news
```

## Run

```bash
uv run main.py --fetch True --analyze True --verbose True
```

... WIP

WIP Pinouts ... 

...

DOCKER
...

Build 

```bash
docker build -t world-theme-music .
```

docker build: The command to build an image from a Dockerfile.

-t world-theme-music: This "tags" (or names) our new image world-theme-music, which is how we'll refer to it later.

.: This tells Docker to look for the Dockerfile in the current directory.

This process will take a few minutes as it downloads the base image and installs all the dependencies. Once it finishes successfully, you will have a self-contained, ready-to-use image of your application. We can then proceed to the next step: testing it.

### Test the Song Generator

```bash
docker run --rm -it \
  --dns=8.8.8.8 \
  -v ./music_generated:/app/music_generated \
  -v ./news_data_cache:/app/news_data_cache \
  --env-file .env \
  world-theme-music \
  uv run python main.py --fetch true --play false
```

- `docker run`: The command to start a new container.
- `--rm`: This is a cleanup flag. It automatically removes the container after it exits, which is perfect for our temporary generation task.
- `-it`: This runs the container in "interactive mode," which allows you to see the script's output (the logs) in your terminal.
- `-v ./music_generated:/app/music_generated`: This is very important. It creates a "volume," which syncs the music_generated folder on your Pi with the /app/music_generated folder inside the container. This allows the container to save the newly created song directly onto your Pi's filesystem.
- `-v ./news_data_cache:/app/news_data_cache`: This does the same for a new cache directory, so your news data isn't re-downloaded every time if you don't use --fetch true.
- `--env-file .env`: This securely passes your API keys from your local .env file into the container so the script can access them.
- `world-theme-music`: This is the name of the image we're using.
- `python main.py --fetch true --play false`: This is the command that will be executed inside the container.


### Test the Hardware Player

```bash
docker run --rm -it \
  --dns=8.8.8.8 \
  --privileged \
  -v /dev/snd:/dev/snd \
  -v ./music_generated:/app/music_generated \
  world-theme-music
```

- `--device /dev/snd`: This gives the container direct access to your Raspberry Pi's sound card.

or in daemon mode (no keyboard interaction....  )

```bash
docker run --rm --name world-theme-player \
  --privileged \
  -v /dev/snd:/dev/snd \
  -v ./music_generated:/app/music_generated \
  world-theme-music \
  uv run python run_player.py --daemon
```


### Run as a service 

music player 

[music-player.service](music-player.service)

check logs:

```bash
docker logs -f world-theme-player
```

### Run cron for fetcher and generator ...

```bash
crontab -e

# Select nano as the editor
# Then at the bottom, add:
0 3 * * * /usr/bin/docker run --rm --name world-theme-generator --dns=8.8.8.8 -v /home/pi/daily_mood_theme_song_player/music_generated:/app/music_generated -v /home/pi/daily_mood_theme_song_player/news_data_cache:/app/news_data_cache --env-file /home/pi/daily_mood_theme_song_player/.env world-theme-music uv run python main.py --fetch true --play false >> /home/pi/daily_mood_theme_song_player/cron.log 2>&1
```

### gen music file size management

TBD 

```bash
crontab -e

# Select nano as the editor
# Then at the bottom, add:
40 2 * * * cd /home/pi/daily_mood_theme_song_player && /home/pi/.local/bin/uv run python tools/bkp_gen_music.py >> /home/pi/daily_mood_theme_song_player/backup.log 2>&1
```

Why this order?

- `2:40 AM` — Backup runs: syncs existing files to Dropbox, cleans up if > `100MB`
- `3:00 AM` — Generator runs: creates new song in clean folder

This ensures all old songs are backed up before cleanup, and the new song has space.

List all cron jobs:

```bash
crontab -l
```

...

TBD 

...

---


### Setup Button based shutdown and wake-up

#### Disable I2C

>[!Warning]
> For this step we need to disable `I2C` as we will be using `GPIO3` (based on Kernel) which is the I2C's `SCL` line using `sudo raspi-config`

| Steps | View |
| --- | --- |
| 1. Open raspi-config & Select *Interface Options* | ![alt text](assets/disableI2c_step1.png) |
| 2. Select I2C Option | ![alt text](assets/disableI2c_step2.png) |
| 3. Disable it (Select *No*) | ![alt text](assets/disableI2c_step3.png) |
| 4. Then hit *Finish* and Reboot | ![alt text](assets/disableI2c_step4.png) |

### Update dtoverlay to allow button ctrl for boot management

Add the following in the `/boot/firmware/config.txt`

```bash
sudo nano /boot/firmware/config.txt
```

Then, after these two lines ...

```bash
# ...
# Additional overlays and parameters are documented
# /boot/firmware/overlays/README
# ...
```

Add ...

```bash
dtoverlay=gpio-shutdown
```

So it now looks like this:

```bash
# ...
# Additional overlays and parameters are documented
# /boot/firmware/overlays/README
dtoverlay=gpio-shutdown
# ...
```

Reboot & Test. 

Now after pi boots, if you press the GPIO3 button, it will go to sleep and if you press again GPIO 3, it will boot back up.  


---

## LICENSE

[unlicense](LICENSE)


