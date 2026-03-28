#!/bin/bash
set -e
# Set ANTHROPIC_API_KEY in your environment before running
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "Error: ANTHROPIC_API_KEY is not set"
    exit 1
fi

echo "=== Natural run 1/2 ==="
python relay.py natural
echo "=== Natural run 2/2 ==="
python relay.py natural
echo "=== Forced 30 run 1/2 ==="
python relay.py forced 30
echo "=== Forced 30 run 2/2 ==="
python relay.py forced 30
echo "=== Claims run 1/3 ==="
python relay.py claims
echo "=== Claims run 2/3 ==="
python relay.py claims
echo "=== Claims run 3/3 ==="
python relay.py claims
echo "=== Claims-forced 30 run 1/3 ==="
python relay.py claims-forced 30
echo "=== Claims-forced 30 run 2/3 ==="
python relay.py claims-forced 30
echo "=== Claims-forced 30 run 3/3 ==="
python relay.py claims-forced 30
echo "=== Blind run 1/3 ==="
python relay.py blind
echo "=== Blind run 2/3 ==="
python relay.py blind
echo "=== Blind run 3/3 ==="
python relay.py blind
echo "=== ALL RUNS COMPLETE ==="
