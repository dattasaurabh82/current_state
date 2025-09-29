# README

## ToDo

### Low

- slow down track for 30 sec to make it feel longer [post processing]
- Send cancel to other agent calls
- maybe web ui
- Dockerization ...
- Docu ...

### High

- HW sensor plugin ...
- Business logic of operation ...

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
sudo apt update && sudo apt install -y build-essential libssl-dev zlib1g-dev libbz2-dev \
libreadline-dev libsqlite3-dev curl libncursesw5-dev xz-utils tk-dev libxml2-dev \
libxmlsec1-dev libffi-dev liblzma-dev
```

### Install UV;

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Install docker 

https://docs.docker.com/engine/install/raspberry-pi-os/


## Project setup

1. git clone
2. uv sync

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

---

## LICENSE

[unlicense](LICENSE)


