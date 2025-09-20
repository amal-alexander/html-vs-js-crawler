#!/bin/bash

# Add Google Chrome's official repository
wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add -
sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list'

# Update package lists and install Google Chrome
apt-get -y update
apt-get install -y google-chrome-stable
