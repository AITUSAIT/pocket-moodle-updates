# Pocket Moodle Updates Service

## Overview
This is a updates service that sends notifications to users.

## Prerequisites
- Docker

## Running the Service

### 1. Clone the Repository
```bash
git clone https://github.com/AITUSAIT/pocket-moodle-updates.git
cd pocket-moodle-updates
```

### 2. provide environment variables
```
TOKEN="bot token"
IS_UPDATE_CONTENT="1"

PM_HOST="host to pocket-moodle-api"
PM_TOKEN="token" //tocken from servers table to be able to send request to pocket-moodle-api

TZ="Asia/Aqtobe"
```

### 3. Build docker image
```bash
docker build --env .env --tag <image tag> .
```

### 4. Run docker container
```bash
docker run --env-file .env -d <image tag>
```

## License
This project is licensed under the GNU General Public License. See the `LICENSE` file for more details.

