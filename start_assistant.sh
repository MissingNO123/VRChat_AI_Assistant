#!/usr/bin/env bash

# Check if running inside a venv
if [ -z "$VIRTUAL_ENV" ]; then
    echo "Virtual environment not detected. It is recommended to run this script inside a Python virtual environment."
    read -p "Do you want to continue anyway? (y/N): " choice
    case "$choice" in
        y|Y ) echo "Continuing without a virtual environment.";;
        * ) echo "Exiting. Please activate a virtual environment and try again."; exit 1;;
    esac
fi

python ./assistant.py
