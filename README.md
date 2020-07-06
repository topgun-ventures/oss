# Bot

## Local development environment setup

### Install PostgreSQL

### Create virtual env

```shell script
python -m venv ./venv
source ./venv/bin/activate
```

### Install dependencies

```shell script
pip install --upgrade pip
pip install wheel
pip install -r requirements.txt
```

### Copy `.env.example` to `.env` and replace environment variables

### Run migrations

```shell script
python lib_common/manage.py db migrate
python lib_common/manage.py db upgrade
```
