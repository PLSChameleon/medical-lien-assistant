#!/bin/bash

# Medical Lien Assistant Launcher for Mac/Linux

echo "Starting Medical Lien Assistant..."
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed"
    echo "Please install Python 3.8 or higher"
    exit 1
fi

# Get the directory of this script
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Change to the script directory
cd "$DIR"

# Check if the launcher file exists
if [ ! -f "multi_user_launcher.py" ]; then
    echo "ERROR: multi_user_launcher.py not found"
    echo "Please run this script from the ai_assistant directory"
    exit 1
fi

# Launch the application
python3 multi_user_launcher.py

# Check exit status
if [ $? -ne 0 ]; then
    echo ""
    echo "Application exited with an error."
    read -p "Press Enter to continue..."
fi