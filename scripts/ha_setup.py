#!/usr/bin/env python3
# scripts/ha_setup.py — met à jour la section home_assistant dans neron.yaml

import sys
import yaml

def main():
    if len(sys.argv) != 4:
        print("Usage: ha_setup.py <yaml_path> <url> <token>")
        sys.exit(1)

    yaml_path = sys.argv[1]
    url       = sys.argv[2]
    token     = sys.argv[3]

    with open(yaml_path, "r") as f:
        config = yaml.safe_load(f)

    if "home_assistant" not in config:
        config["home_assistant"] = {}

    config["home_assistant"]["enabled"] = True
    config["home_assistant"]["url"]     = url
    config["home_assistant"]["token"]   = token

    with open(yaml_path, "w") as f:
        yaml.dump(config, f, allow_unicode=True, default_flow_style=False)

    print("✔ neron.yaml mis à jour")

if __name__ == "__main__":
    main()
