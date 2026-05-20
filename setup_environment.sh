#!/bin/bash
# Installation script for macOS and Ubuntu

OS_TYPE=$(uname)

echo "Detecting OS: $OS_TYPE"

if [ "$OS_TYPE" == "Darwin" ]; then
    # macOS
    echo "Installing dependencies for macOS..."
    brew install python@3.10 cmake mosquitto wget
elif [ -f /etc/lsb-release ]; then
    # Ubuntu
    echo "Installing dependencies for Ubuntu..."
    sudo apt update
    sudo apt install -y python3.10 python3-pip cmake libmosquitto-dev build-essential clang
fi

echo "Basic toolchain installed. For Flutter (Dart), please follow the official guide as it requires manual path configuration."
