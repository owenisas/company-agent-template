#!/usr/bin/env bash
# Install a systemd --user unit for this checkout's webui.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
UNIT_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
UNIT="$UNIT_DIR/hermes-webui.service"

mkdir -p "$UNIT_DIR" "$ROOT/runtime"

if [[ ! -f "$ROOT/runtime/secret" ]]; then
  umask 077
  python3 - <<'PY' > "$ROOT/runtime/secret"
import secrets
print(secrets.token_urlsafe(48))
PY
  chmod 600 "$ROOT/runtime/secret"
  echo "wrote $ROOT/runtime/secret"
fi

if [[ ! -f "$ROOT/runtime/webui.env" && -f "$ROOT/runtime/webui.env.EXAMPLE" ]]; then
  cp "$ROOT/runtime/webui.env.EXAMPLE" "$ROOT/runtime/webui.env"
  chmod 600 "$ROOT/runtime/webui.env"
fi

chmod +x "$ROOT/run.sh"

cat > "$UNIT" <<EOF
[Unit]
Description=Company Hermes profile chat webui
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=$ROOT
Environment=WEBUI_PORT=8080
Environment=WEBUI_BIND=0.0.0.0
EnvironmentFile=-$ROOT/runtime/webui.env
ExecStart=$ROOT/run.sh
Restart=on-failure
RestartSec=5
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=default.target
EOF

systemctl --user daemon-reload
systemctl --user enable hermes-webui.service
echo "Installed $UNIT"
echo "Start with:  systemctl --user start hermes-webui.service"
echo "Logs:        journalctl --user -u hermes-webui -f"
echo "Users file:  $ROOT/runtime/users.json  (see USERS.example.json)"
echo "Enable linger if this should survive logout: loginctl enable-linger \"\$USER\""
