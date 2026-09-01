#!/bin/bash

echo "🚀 Initializing QuakeGuard Command Center..."

# Get absolute paths dynamically based on script location
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Auto-generate secrets on first boot
if [[ ! -f "$PROJECT_ROOT/backend/.env" ]]; then
    echo "⚠️  First boot detected: backend/.env not found."
    echo "🔐 Running secret generator to provision fresh .env files..."
    "$SCRIPT_DIR/generate_secrets.sh"
    echo ""
fi

echo "🌐 Running tunnel automation..."
"$SCRIPT_DIR/tunnel_init.sh"
if [[ $? -ne 0 ]]; then
    echo "❌ Tunnel script failed. Aborting."
    exit 1
fi
echo ""

echo "🖥️ Opening 3 separate terminal windows (Ptyxis)..."

# 1. Backend Window
ptyxis --new-window -d "$PROJECT_ROOT/backend" -T "Backend (Docker)" -- bash -c "echo '=== BACKEND (Docker) ==='; docker compose --profile ai up --build; exec bash" &

# 2. Mobile Window
# Adding a small delay so windows don't overlap completely at spawn
sleep 0.5
ptyxis --new-window -d "$PROJECT_ROOT/mobile" -T "Mobile (Expo)" -- bash -c "echo '=== MOBILE (Expo) ==='; npx expo start --clear; exec bash" &

# 3. Firmware Window (Wait 30s for the Backend to be fully ready)
sleep 0.5
ptyxis --new-window -d "$PROJECT_ROOT/firmware" -T "IoT (ESP32)" -- bash -c "echo '=== IoT (ESP32) ==='; echo '⏳ Waiting 30 seconds for the backend to start...'; sleep 30; echo '🚀 Flashing new firmware with updated Cloudflare URL...'; pio run -t upload -t monitor; exec bash" &

echo "✅ All terminals launched successfully!"
echo "You can close this window now. Your 3 QuakeGuard terminals are running independently."
