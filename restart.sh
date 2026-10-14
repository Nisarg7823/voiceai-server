#!/usr/bin/env bash
# Rebuild the agent image, replace the running container, and tail its logs.
#
#   ./restart.sh              rebuild, restart, clear the room, follow logs
#   ./restart.sh --no-build   skip the image build (use when only .env changed)
#   ./restart.sh --keep-room  leave the LiveKit room alone

set -euo pipefail
cd "$(dirname "$0")"

IMAGE=my-app
CONTAINER=voiceai-agent
ROOM=test-room
BUILD=1
CLEAR_ROOM=1

for arg in "$@"; do
  case "$arg" in
    --no-build)  BUILD=0 ;;
    --keep-room) CLEAR_ROOM=0 ;;
    *) echo "unknown option: $arg" >&2; exit 2 ;;
  esac
done

# --- checks -----------------------------------------------------------------
[ -f .env ] || { echo "ERROR: no .env in $(pwd)" >&2; exit 1; }

missing=()
for key in LIVEKIT_URL LIVEKIT_API_KEY LIVEKIT_API_SECRET \
           GROQ_API_KEY DEEPGRAM_API_KEY SARVAM_API_KEY; do
  grep -qE "^${key}=.+" .env || missing+=("$key")
done
if [ ${#missing[@]} -gt 0 ]; then
  echo "ERROR: .env is missing or has empty values for: ${missing[*]}" >&2
  exit 1
fi

docker info >/dev/null 2>&1 || { echo "ERROR: Docker isn't running." >&2; exit 1; }

# --- build ------------------------------------------------------------------
if [ "$BUILD" -eq 1 ]; then
  echo "==> Building $IMAGE"
  docker build -t "$IMAGE" .
else
  echo "==> Skipping build"
fi

# --- replace the container --------------------------------------------------
echo "==> Removing old container (if any)"
docker rm -f "$CONTAINER" >/dev/null 2>&1 || true

echo "==> Starting $CONTAINER"
docker run -d --name "$CONTAINER" --env-file .env \
  -e DB_PATH=/app/data/complaints.db \
  -v voiceai-db:/app/data \
  -p 3001:8081 "$IMAGE" >/dev/null

# --- clear the room ---------------------------------------------------------
# close_on_disconnect=False means the agent lingers after you leave and won't
# greet you again on rejoin, so delete the room for a clean run.
if [ "$CLEAR_ROOM" -eq 1 ]; then
  if command -v lk >/dev/null 2>&1; then
    echo "==> Clearing room '$ROOM'"
    set -a; . ./.env; set +a
    lk room delete --url "$LIVEKIT_URL" \
                   --api-key "$LIVEKIT_API_KEY" \
                   --api-secret "$LIVEKIT_API_SECRET" \
                   "$ROOM" >/dev/null 2>&1 \
      && echo "    room deleted" \
      || echo "    nothing to delete"
  else
    echo "==> 'lk' not found, skipping room cleanup"
  fi
fi

# --- logs -------------------------------------------------------------------
echo
echo "==> Agent is up. Reload the client page and click Start."
echo "    Ctrl-C stops following logs; the container keeps running."
echo
exec docker logs -f "$CONTAINER"
