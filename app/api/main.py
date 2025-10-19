# file: app.py
import os
import sys
import base64
import requests
from flask import Flask, request, jsonify

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ingest import RawPublisher

BOT_TOKEN = os.getenv("BOT_TOKEN")  # coloque no ambiente
if not BOT_TOKEN:
    raise RuntimeError("Defina BOT_TOKEN no ambiente.")

TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"
TELEGRAM_FILE_API = f"https://api.telegram.org/file/bot{BOT_TOKEN}"

app = Flask(__name__)
publisher = RawPublisher(auto_connect=True)


def tg_send_message(chat_id: int, text: str) -> None:
    try:
        requests.post(f"{TELEGRAM_API}/sendMessage", json={"chat_id": chat_id, "text": text}, timeout=15)
    except Exception:
        pass


def tg_get_file_bytes(file_id: str) -> bytes:
    # 1) resolve file_path
    r1 = requests.get(f"{TELEGRAM_API}/getFile", params={"file_id": file_id}, timeout=15)
    r1.raise_for_status()
    file_path = r1.json()["result"]["file_path"]
    # 2) baixa bytes
    r2 = requests.get(f"{TELEGRAM_FILE_API}/{file_path}", timeout=60)
    r2.raise_for_status()
    return r2.content


@app.route("/telegram-webhook", methods=["POST"])
def telegram_webhook():
    u = request.json or {}
    msg = u.get("message") or {}
    chat_id = (msg.get("chat") or {}).get("id")

    if not chat_id:
        return jsonify(success=True)

    # FOTO: pega a maior (última da lista)
    if "photo" in msg:
        file_id = msg["photo"][-1]["file_id"]
        try:
            blob = tg_get_file_bytes(file_id)
            b64 = base64.b64encode(blob).decode("ascii")
            # usa o message_id como source_id
            publisher.publish(source_id=int(msg.get("message_id", 0)),
                              attachment_type="image",
                              attachment_data=b64)
            tg_send_message(chat_id, "✅ Foto recebida e enviada para processamento.")
        except Exception as e:
            tg_send_message(chat_id, f"❌ Erro ao processar a foto: {e}")

        return jsonify(success=True)

    if "document" in msg:
        file_id = msg["document"]["file_id"]
        try:
            blob = tg_get_file_bytes(file_id)
            b64 = base64.b64encode(blob).decode("ascii")
            publisher.publish(source_id=int(msg.get("message_id", 0)),
                              attachment_type="document",
                              attachment_data=b64)
            tg_send_message(chat_id, "✅ Documento recebido e enviado para processamento.")
        except Exception as e:
            tg_send_message(chat_id, f"❌ Erro ao processar o documento: {e}")

        return jsonify(success=True)

    # texto qualquer → instrução simples
    if "text" in msg:
        tg_send_message(chat_id, "Envie uma foto ou PDF que eu encaminho para análise. 📎")

    return jsonify(success=True)

@app.route("/api/send_message", methods=["POST"])
def api_send_message():
    data = request.json or {}
    chat_id = data.get("chat_id")
    text = data.get("text")

    if not chat_id or not text:
        return jsonify({"erro": "chat_id e text são obrigatórios"}), 400

    try:
        tg_send_message(chat_id, text)
        return jsonify({"status": "ok", "mensagem": "enviada"}), 200
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

@app.route("/health", methods=["GET"])
def health():
    return jsonify(ok=True)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "3000")), debug=True)
