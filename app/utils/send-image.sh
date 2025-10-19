#!/usr/bin/env sh

set -eu

BOOTSTRAP="${BOOTSTRAP:-localhost:29092}"
TOPIC="${TOPIC:-btg.raw}"
SOURCE_ID="${SOURCE_ID:-1}"

usage() {
  echo "Uso: $0 <imagem> [--bootstrap HOST:PORT] [--topic TOPIC] [--source-id N]" >&2
  exit 1
}

[ $# -lt 1 ] && usage
IMG="$1"; shift
while [ $# -gt 0 ]; do
  case "$1" in
    --bootstrap) BOOTSTRAP="$2"; shift 2;;
    --topic)     TOPIC="$2"; shift 2;;
    --source-id) SOURCE_ID="$2"; shift 2;;
    -h|--help)   usage;;
    *) echo "Arg desconhecido: $1" >&2; usage ;;
  esac
done

[ -f "$IMG" ] || { echo "Arquivo não encontrado: $IMG" >&2; exit 2; }

JSON="$(python3 - "$IMG" "$SOURCE_ID" <<'PY'
import sys, base64, json, time
img_path = sys.argv[1]
source_id = int(sys.argv[2])
with open(img_path, "rb") as f:
    b64 = base64.b64encode(f.read()).decode("ascii")  # sem quebras, padding correto
obj = {
    "source_id": source_id,
    "attachment_type": "image",
    "attachment_data": b64,
    "timestamp": int(time.time())
}
print(json.dumps(obj, ensure_ascii=False, separators=(",", ":")))
PY
)"

len_mod=$(( ${#JSON} % 4 ))

if command -v kcat >/dev/null 2>&1; then
  printf '%s\n' "$JSON" | kcat -b "$BOOTSTRAP" -t "$TOPIC"
  echo "Enviado com kcat para $BOOTSTRAP/$TOPIC" >&2
elif command -v kafkacat >/dev/null 2>&1; then
  printf '%s\n' "$JSON" | kafkacat -b "$BOOTSTRAP" -t "$TOPIC"
  echo "Enviado com kafkacat para $BOOTSTRAP/$TOPIC" >&2
elif command -v kafka-console-producer.sh >/dev/null 2>&1; then
  printf '%s\n' "$JSON" | kafka-console-producer.sh --bootstrap-server "$BOOTSTRAP" --topic "$TOPIC" >/dev/null
  echo "Enviado com kafka-console-producer.sh para $BOOTSTRAP/$TOPIC" >&2
else
  echo "Erro: instale 'kcat' (kafkacat) ou 'kafka-console-producer.sh' no PATH." >&2
  exit 3
fi
