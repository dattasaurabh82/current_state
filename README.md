# README

## ToDo

### Low

- slow down track for 30 sec to make it feel longer [post processing]
- Other region of news 
- Send cancel to other agent calls
- WIP: Docu ...

### High

- Autostart docker & cron 
- Blink factor
- Pin and other configs as ext vars ...
- WIP: All code base cleanup 
- HW sensor plugin
- Business logic of operation ...

### Backlog

- How often and how long silent audio player plays
  - Currently happy with the implementation
- maybe web ui

### Bug

- silent audio to keep the channel active did not work ....


---

## Project structure

```txt
.
├── README.md
├── pyproject.toml
├── config.json
├── main.py
├── lib
│   ├── __init__.py
│   ├── llm_analyzer.py
│   ├── music_generator.py
│   ├── music_post_processor.py
│   ├── news_fetcher.py
│   └── player.py
├── llm_agents
│   ├── __init__.py
│   ├── musicgen_prompt_crafter.py
│   └── news_analyzer.py
├── prompts
│   ├── musicgen_prompt_crafter_system.md
│   └── news_analyzer_system.md
├── music_generated/*
├── LICENSE
└── uv.lock
```

### Install Python Build Dependencies:

```bash
sudo apt update && sudo apt install -y python3-dev build-essential libssl-dev zlib1g-dev libbz2-dev \
libreadline-dev libsqlite3-dev curl libncursesw5-dev xz-utils tk-dev libxml2-dev \
libxmlsec1-dev libffi-dev liblzma-dev -y

sudo apt install python3-dev -y
```

### Install Audio deps

```bash
sudo apt-get install libportaudio2 -y
```

### Install UV;

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

### Create an API key for newsapi.org

```bash
touch .env
nano .env
```

Update `NEWS_API_KEY`

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


---

## LICENSE

[unlicense](LICENSE)


