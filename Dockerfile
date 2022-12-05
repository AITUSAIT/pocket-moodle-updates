FROM ubuntu:22.04

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV TZ=Asia/Almaty

COPY requirements.txt .

RUN apt-get update -y && apt-get upgrade -y && \
    apt-get install -yqq --no-install-recommends python3 python3-pip wget unzip tzdata && \
    pip3 install -r requirements.txt && \
    wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb && \
    apt install -y ./google-chrome-stable_current_amd64.deb && \
    rm google-chrome-stable_current_amd64.deb && \
    wget https://chromedriver.storage.googleapis.com/107.0.5304.62/chromedriver_linux64.zip && \
    unzip chromedriver_linux64.zip && \
    mv chromedriver /usr/bin/chromedriver && \
    chmod +x /usr/bin/chromedriver && \
    ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone && \
    dpkg-reconfigure --frontend noninteractive tzdata \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*


WORKDIR /pocket-moodle-updates
COPY . /pocket-moodle-updates

EXPOSE 8000

RUN adduser -u 5678 --disabled-password --gecos "" appuser && chown -R appuser /pocket-moodle-updates
USER appuser

CMD ["python3", "main.py"]
