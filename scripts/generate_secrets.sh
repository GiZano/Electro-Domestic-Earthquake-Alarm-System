#!/bin/bash
# ==============================================================================
# QuakeGuard Secrets Generator & Sync Utility
# ==============================================================================

# Ensure we are in the project root
if [ ! -f "backend/.env.example" ]; then
    echo "❌ Error: Please run this script from the root of the QuakeGuard project."
    exit 1
fi

prompt_yes_no() {
    if [ "$CI" = "true" ]; then
        echo "$1 [y/n]: y (Auto-yes in CI)"
        return 0
    fi
    while true; do
        read -p "$1 [y/n]: " yn
        case $yn in
            [Yy]* ) return 0;;
            [Nn]* ) return 1;;
            * ) echo "Please answer yes or no.";;
        esac
    done
}

prompt_choice() {
    local prompt="$1"
    local options="$2"
    if [ "$CI" = "true" ]; then
        # Default to 'b' (backend) in CI for safety
        echo "$prompt b (Auto-selected in CI)" >&2
        echo "b"
        return 0
    fi
    while true; do
        read -p "$prompt " choice
        choice=$(echo "$choice" | tr '[:upper:]' '[:lower:]')
        if [[ " $options " =~ " $choice " ]]; then
            echo "$choice"
            return 0
        else
            echo "Invalid choice. Please enter one of: $options" >&2
        fi
    done
}

echo "🔍 Analyzing current QuakeGuard configuration..."

# 1. Ensure all files exist before checking mismatches
if [ ! -f "backend/.env" ]; then
    echo "⚠️  backend/.env is missing."
    if prompt_yes_no "Do you want to create it and generate fresh random secrets?"; then
        cp backend/.env.example backend/.env
        sed -i "s/your_enrollment_token/$(openssl rand -hex 32)/g" backend/.env
        sed -i "s/your_iot_api_key/$(openssl rand -hex 32)/g" backend/.env
        sed -i "s/your_mobile_ws_token/$(openssl rand -hex 32)/g" backend/.env
        echo "✅ backend/.env created with fresh secrets."
    else
        echo "❌ Cannot proceed without backend/.env."
        exit 1
    fi
fi

if [ ! -f "mobile/.env" ]; then
    echo "⚠️  mobile/.env is missing. Creating from template..."
    cp mobile/.env.example mobile/.env
fi

if [ ! -f "firmware/esp32_config.env" ]; then
    echo "⚠️  firmware/esp32_config.env is missing. Creating from template..."
    cp firmware/esp32_config.env.example firmware/esp32_config.env
fi

# 2. Extract current secrets from all files
BACKEND_ENROLLMENT=$(grep -E "^ENROLLMENT_TOKEN=" backend/.env | cut -d '=' -f 2- | tr -d ' "\r')
BACKEND_IOT=$(grep -E "^IOT_API_KEY=" backend/.env | cut -d '=' -f 2- | tr -d ' "\r')
BACKEND_MOBILE=$(grep -E "^MOBILE_WS_TOKEN=" backend/.env | cut -d '=' -f 2- | tr -d ' "\r')

MOBILE_IOT=$(grep -E "^EXPO_PUBLIC_IOT_API_KEY=" mobile/.env | cut -d '=' -f 2- | tr -d ' "\r')
MOBILE_WS=$(grep -E "^EXPO_PUBLIC_MOBILE_WS_TOKEN=" mobile/.env | cut -d '=' -f 2- | tr -d ' "\r')

FW_ENROLLMENT=$(grep -E "^ENROLLMENT_TOKEN=" firmware/esp32_config.env | cut -d '=' -f 2- | tr -d ' "\r')

# 3. Global Mismatch Check
if [ "$MOBILE_IOT" != "$BACKEND_IOT" ] || [ "$MOBILE_WS" != "$BACKEND_MOBILE" ] || [ "$FW_ENROLLMENT" != "$BACKEND_ENROLLMENT" ]; then
    echo ""
    echo "⚠️  GLOBAL MISMATCH DETECTED: The secrets across backend, mobile, and firmware are not synchronized."
    echo "   If you modified one configuration manually, choose it as the 'Source of Truth'."
    echo ""
    choice=$(prompt_choice "Which component should override the others? (b=backend, m=mobile, f=firmware):" "b m f")
    
    if [ "$choice" = "b" ]; then
        # Backend overrides all
        sed -i "s/^EXPO_PUBLIC_IOT_API_KEY=.*/EXPO_PUBLIC_IOT_API_KEY=$BACKEND_IOT/g" mobile/.env
        sed -i "s/^EXPO_PUBLIC_MOBILE_WS_TOKEN=.*/EXPO_PUBLIC_MOBILE_WS_TOKEN=$BACKEND_MOBILE/g" mobile/.env
        sed -i "s/^ENROLLMENT_TOKEN=.*/ENROLLMENT_TOKEN=$BACKEND_ENROLLMENT/g" firmware/esp32_config.env
        echo "✅ Mobile and Firmware synced with Backend."
    elif [ "$choice" = "m" ]; then
        # Mobile overrides backend (for mobile keys), firmware aligns to backend enrollment
        sed -i "s/^IOT_API_KEY=.*/IOT_API_KEY=$MOBILE_IOT/g" backend/.env
        sed -i "s/^MOBILE_WS_TOKEN=.*/MOBILE_WS_TOKEN=$MOBILE_WS/g" backend/.env
        sed -i "s/^ENROLLMENT_TOKEN=.*/ENROLLMENT_TOKEN=$BACKEND_ENROLLMENT/g" firmware/esp32_config.env
        echo "✅ Backend synced with Mobile. Firmware aligned with Backend."
    elif [ "$choice" = "f" ]; then
        # Firmware overrides backend enrollment, mobile aligns to backend keys
        sed -i "s/^ENROLLMENT_TOKEN=.*/ENROLLMENT_TOKEN=$FW_ENROLLMENT/g" backend/.env
        sed -i "s/^EXPO_PUBLIC_IOT_API_KEY=.*/EXPO_PUBLIC_IOT_API_KEY=$BACKEND_IOT/g" mobile/.env
        sed -i "s/^EXPO_PUBLIC_MOBILE_WS_TOKEN=.*/EXPO_PUBLIC_MOBILE_WS_TOKEN=$BACKEND_MOBILE/g" mobile/.env
        echo "✅ Backend synced with Firmware. Mobile aligned with Backend."
    fi
else
    echo "✅ All local secrets are perfectly synchronized!"
fi

# --- HiveMQ Check ---
if grep -q "your_mqtt_username" backend/.env || grep -q "your-cluster-id" backend/.env; then
    echo ""
    echo "⚠️  ACTION REQUIRED: HiveMQ Credentials Missing!"
    echo "   The MQTT Broker is vital for QuakeGuard telemetry."
    echo "   Please create a free cluster at: https://console.hivemq.cloud/"
    echo "   Then, manually configure the following in backend/.env and firmware/esp32_config.env:"
    echo "     - MQTT_BROKER"
    echo "     - MQTT_USERNAME"
    echo "     - MQTT_PASSWORD"
    echo ""
    prompt_yes_no "I understand, I will configure HiveMQ manually later. Continue?" || exit 1
fi

echo ""
echo "🚀 Environment secrets synchronization complete!"
