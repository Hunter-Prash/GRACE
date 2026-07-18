#!/bin/bash
# Load NVM so Node.js is available to the background subprocess
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"

cd /home/prashant-rajaji/Desktop/PERSONAL/GRACE
source venv/bin/activate
python main.py

# Forcefully clean up the Node.js backend port to prevent orphaned background processes
fuser -k 3000/tcp >/dev/null 2>&1 || true
