# Deployment Guide for Rocky 9

This guide explains how to deploy your **"WealthWarden"** (Project Name Idea 1) on your Rocky 9 server as a background service.

## Prerequisites
On your Rocky 9 server, install Docker (or Podman-Docker):
```bash
sudo dnf config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
sudo dnf install docker-ce docker-ce-cli containerd.io docker-compose-plugin
sudo systemctl start docker
sudo systemctl enable docker
```

## Deployment Steps

1.  **Transfer Files**: Upload the project folder to your server (e.g., `/opt/finance_bot`).
    ```bash
    scp -r /path/to/FinanceAssistant user@your-server:/opt/finance_bot
    ```

    > **💡 Pro Tip: Efficient Updates (Only changed files)**
    > use `rsync` instead of `scp` to upload only the files that have changed. It's much faster!
    > ```bash
    > # Run this from inside your Project folder
    > rsync -avz --exclude 'data' --exclude '.env' --exclude '.git' ./ root@65.49.198.80:/home/zenithjolt/finance_bot
    > ```
    > *   `-a`: Archive mode (keeps permissions)
    > *   `-v`: Verbose (shows progress)
    > *   `-z`: Compress (faster transfer)
    > *   `--exclude`: IMPORTANT! Don't overwrite your production DB or .env file.


2.  **Configure Environment**:
    SSH into your server and create the `.env` file with your real keys.
    ```bash
    cd /opt/finance_bot
    cp .env.example .env
    nano .env
    # Paste your TELEGRAM_BOT_TOKEN and GEMINI_API_KEY
    ```

3.  **Run as a Service**:
    We use Docker Compose to build and run the bot in the background.
    ```bash
    docker compose up -d --build
    ```
    *   `-d`: Detached mode (runs in background).
    *   `--build`: Rebuilds the image if code changed.
    *   `restart: always`: (Configured in `docker-compose.yml`) Auto-starts on boot.

4.  **View Logs**:
    To see what the bot is doing:
    ```bash
    docker compose logs -f
    ```

5.  **Stop/Update**:
    ```bash
    docker compose down       # Stop
    git pull ...              # Get new code
    docker compose up -d --build # Restart with new code
    ```

## Alternative: Systemd (Native Service)
If you prefer NOT to use Docker:

1.  Create a service file: `/etc/systemd/system/finance-bot.service`
    ```ini
    [Unit]
    Description=Finance Bot Service
    After=network.target

    [Service]
    Type=simple
    User=root
    WorkingDirectory=/opt/finance_bot
    ExecStart=/usr/bin/python3 /opt/finance_bot/main.py
    Restart=always
    EnvironmentFile=/opt/finance_bot/.env

    [Install]
    WantedBy=multi-user.target
    ```
2.  Enable and start:
    ```bash
    sudo systemctl daemon-reload
    sudo systemctl enable finance-bot
    sudo systemctl start finance-bot
    ```
