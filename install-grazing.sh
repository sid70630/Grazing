#!/usr/bin/env bash
set -Eeo pipefail

GRAZING_HOME="$HOME/grazing"
ARCHIVE="grazing_env.tar.gz"
URL="https://www.to.infn.it/~nanni/grazing/$ARCHIVE"

mkdir -p "$GRAZING_HOME"
cd "$GRAZING_HOME"

if [[ ! -f "$ARCHIVE" ]]; then
  wget "$URL"
else
  echo "SKIP: $ARCHIVE already exists"
fi

if [[ ! -d data || ! -f grazing_9_64bit ]]; then
  tar -xzf "$ARCHIVE"
else
  echo "SKIP: GRAZING files are already extracted"
fi

chmod +x grazing_9 grazing_9_64bit

if ! grep -Fq '# GRAZING' "$HOME/.bashrc"; then
  cat >> "$HOME/.bashrc" <<'EOF'

# GRAZING
export GRAZING_DIR="$HOME/grazing/data"
export PATH="$HOME/grazing:$PATH"
EOF
fi

export GRAZING_DIR="$GRAZING_HOME/data"
export PATH="$GRAZING_HOME:$PATH"

[[ -d "$GRAZING_DIR" ]] || { echo "ERROR: GRAZING data directory not found"; exit 1; }
[[ -x "$GRAZING_HOME/grazing_9_64bit" ]] || { echo "ERROR: 64-bit executable not found"; exit 1; }

echo "GRAZING installed successfully."
echo "Executable: $GRAZING_HOME/grazing_9_64bit"
echo "Data:       $GRAZING_DIR"
echo "Open a new terminal and run: grazing_9_64bit"
