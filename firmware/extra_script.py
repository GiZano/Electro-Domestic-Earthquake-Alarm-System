import os

Import("env")

config_path = "esp32_config.env"

print(f"Looking for configuration in: {config_path}")

if os.path.isfile(config_path):
    print("Config file found! Injecting environment variables...")
    try:
        with open(config_path) as f:
            for line in f:
                if line.strip().startswith("#") or not line.strip():
                    continue
                if "=" in line:
                    key, value = line.strip().split("=", 1)
                    value = value.strip().strip('"').strip("'")
                    if value.isdigit():
                        env_value = value
                    else:
                        env_value = f'\\"{value}\\"'
                    print(f"   Setting {key} = {value}")
                    env.Append(CPPDEFINES=[(key, env_value)])
    except Exception as e:
        print(f"Error reading config file: {e}")
else:
    print(f"WARNING: {config_path} not found! Using default/fallback values if defined in code.")