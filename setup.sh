#!/bin/bash

# Create a setup script for Streamlit Cloud
# This installs Google Chrome and ChromeDriver for Selenium

set -e

# Update package lists
apt-get update

# Download and install Chrome
echo "Installing Google Chrome..."
wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add -
echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list
apt-get update
apt-get install -y google-chrome-stable

# Verify Chrome installation
if command -v google-chrome-stable &> /dev/null; then
    echo "Google Chrome installed successfully"
    google-chrome-stable --version
else
    echo "Chrome installation failed"
    exit 1
fi

# Create symlink for easier access
ln -sf /usr/bin/google-chrome-stable /usr/bin/google-chrome

echo "Setup completed successfully!"
