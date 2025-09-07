# README

## post pi first boot setup

```bash
sudo apt-get update -y
sudo apt-get upgrade -y
sudo apt-get install git neofetch -y
```

### Setup pyenv

```bash
curl https://pyenv.run | bash
nano ~/.bashrc
```

Scroll to the very end of the file and paste the following block of code add the following to load pyenv automatically

```bash
export PYENV_ROOT="$HOME/.pyenv"
[[ -d $PYENV_ROOT/bin ]] && export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init - bash)"

# Load pyenv-virtualenv automatically
eval "$(pyenv virtualenv-init -)"
```

Save the file and exit 

Apply the Changes

```bash
exec $SHELL

# Verify:
pyenv --version
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

### Install BATCAT

```bash
sudo apt install bat -y
ln -s /usr/bin/batcat ~/.local/bin/bat
# update path based on which batcat cmd
```

#### Add alias

```bash
sudo nano .bashrc

# Add 
alias cat="batcat"
```

Save and exit and reload (source .bashrc)
then try `cat <some file>`

## Project setup

1. git clone
2. uv sync

Add PYTHON GPIO

In the repo dir:

```bash
sudo apt update && sudo apt install python3-dev -y
uv pip install RPi.GPIO
```

... WIP

### Create an API key for newsapi.org

```bash
touch .env
nano .env
```

Update `NEWS_API_KEY`

...

DOCKER
...



---

## LICENSE

[unlicense](LICENSE)


