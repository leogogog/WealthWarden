# Deployment Guide for Rocky 9

This guide explains how to deploy your **"WealthWarden"** on your server using Git for easy updates.

## Prerequisites
On your Server:
1.  **Install Docker**:
    ```bash
    sudo dnf config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
    sudo dnf install docker-ce docker-ce-cli containerd.io docker-compose-plugin git
    sudo systemctl start docker
    sudo systemctl enable docker
    ```

## 1. Setup Deployment (Switching to Git)

If you previously used `rsync`, you can convert your server folder to a Git repository to enable `git pull` updates.

**On your Server (SSH in):**

```bash
cd /opt/finance_bot  # Or where your project is

# 1. Initialize Git
git init

# TROUBLESHOOTING: If you see "fatal: detected dubious ownership", run:
# git config --global --add safe.directory /opt/finance_bot

# 2. Add the remote repository
git remote add origin https://github.com/leogogog/WealthWarden.git

# 3. Fetch the latest code
git fetch origin

# 4. Reset local files to match remote (⚠️ This overwrites local code changes, but keeps .env / data)
git reset --hard origin/main

# 5. Set upstream for future pulling
git branch --set-upstream-to=origin/main main
```

> **Note**: This will not delete your `.env` file or `db/` folder if they are not tracked in git (which they shouldn't be).

## 2. Configure Environment
Ensure your `.env` file is present.
```bash
cp .env.example .env
nano .env
# Paste TELEGRAM_BOT_TOKEN and GEMINI_API_KEY
```

## 3. Run Service
Start the bot with Docker Compose:

```bash
docker compose up -d --build
```

## 4. How to Update Code
In the future, when you make changes locally:
1.  **Local**: `git push` your changes.
2.  **Server**:
    ```bash
    cd /opt/finance_bot
    git pull
    docker compose up -d --build
    ```

## Alternative: Manual Sync (rsync)
If you prefer not to use git on the server, you can still use rsync:
```bash
rsync -avz --exclude 'data' --exclude '.env' --exclude '.git' ./ root@<IP>:/opt/finance_bot
```
