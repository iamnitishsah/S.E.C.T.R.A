#!/usr/bin/env bash
# One-time setup of a fresh Ubuntu server: Docker, git, make, and swap.
#   ssh -i KEY ubuntu@HOST 'bash -s' < scripts/server_setup.sh
set -euo pipefail

sudo apt-get update -y
sudo apt-get install -y ca-certificates curl git make

if ! command -v docker >/dev/null; then
    curl -fsSL https://get.docker.com | sudo sh
fi
sudo usermod -aG docker "$USER"            # takes effect at the next login

# 2 GB of swap, so MySQL + Qdrant + the API fit on a small instance
if ! sudo swapon --show | grep -q /swapfile; then
    sudo fallocate -l 2G /swapfile
    sudo chmod 600 /swapfile
    sudo mkswap /swapfile
    sudo swapon /swapfile
    echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab >/dev/null
fi

docker --version
docker compose version
free -h | sed -n 1,3p
echo "setup done: log out and back in before using docker"