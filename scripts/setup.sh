#!/bin/bash
set -e

echo "Starting SentinelOps Foundation Setup..."

# 1. Create virtual environment
if [ ! -d ".venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv .venv
else
    echo "Virtual environment already exists."
fi

# 2. Activate and install dependencies
echo "Installing dependencies..."
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 3. Initialize DVC
if [ ! -d ".dvc" ]; then
    echo "Initializing DVC..."
    dvc init
    
    # 4. Create DVC local remote placeholder
    echo "Setting up local DVC remote..."
    mkdir -p /tmp/dvcstore
    dvc remote add -d localremote /tmp/dvcstore
else
    echo "DVC is already initialized."
fi

# 5. Prepare basic directories
echo "Preparing project directories..."
mkdir -p src tests notebooks models artifacts data/raw data/processed

echo "Setup complete! Please run 'source .venv/bin/activate' to activate the virtual environment."
