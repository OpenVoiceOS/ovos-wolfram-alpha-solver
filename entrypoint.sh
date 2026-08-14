#!/bin/sh
# Writes the persona JSON at container start so WOLFRAM_APPID (if set) can
# reach the plugin's "appid" config key. Never echoed or logged: the value
# only ever goes into the JSON file on disk.
#
# If WOLFRAM_APPID is unset, "appid" is left out of the file entirely and
# the plugin falls back to its own bundled demo key
# (ovos_wolfram_alpha_plugin/__init__.py: `key or "Y7R353-9HQAAL8KKA"`).
# That demo key is shared across every user of the plugin and is rate
# limited -- fine for trying this image out, not for real traffic. Get a
# free appid at https://developer.wolframalpha.com/ and set WOLFRAM_APPID
# for anything beyond a quick test.
set -e

mkdir -p /personas

if [ -n "$WOLFRAM_APPID" ]; then
    python3 -c '
import json, os
persona = {
    "name": "WolframBot",
    "handlers": ["ovos-wolfram-alpha-plugin"],
    "ovos-wolfram-alpha-plugin": {"appid": os.environ["WOLFRAM_APPID"]},
}
with open("/personas/wolframbot.json", "w") as f:
    json.dump(persona, f)
'
else
    cat > /personas/wolframbot.json <<'EOF'
{
  "name": "WolframBot",
  "handlers": ["ovos-wolfram-alpha-plugin"]
}
EOF
fi

exec ovos-persona-server --personas-dir /personas --mcp --port 8337 --host 0.0.0.0
