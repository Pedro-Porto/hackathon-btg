# file: api/main.py
import os
import sys
import base64
import requests
from flask import Flask, request, jsonify

# permite importar ingest/ e core/ a partir da raiz do projeto
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Se o pacote 'ingest' não reexportar a classe, use: from ingest.main import RawPublisher
from ingest import RawPublisher  # requer ingest/__init__.py com: from .main import RawPublisher

# -------------------------------------------------------------------
# Config
# -------------------------------------------------------------------
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("Defina BOT_TOKEN no ambiente.")

TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"
TELEGRAM_FILE_API = f"https://api.telegram.org/file/bot{BOT_TOKEN}"

app = Flask(__name__)
publisher = RawPublisher(auto_connect=True)  # usa KAFKA_BROKER_URL e TOPIC_OUT_NAME do ambiente
user_states = {}  # memória simples de estados por chat_id


# -------------------------------------------------------------------
# Utilitários Telegram
# -------------------------------------------------------------------
def tg_send_message(chat_id: int, text: str) -> None:
    try:
        requests.post(
            f"{TELEGRAM_API}/sendMessage",
            json={"chat_id": chat_id, "text": text},
            timeout=15,
        )
    except Exception:
        pass


def tg_get_file_bytes(file_id: str) -> bytes:
    # 1) resolve file_path
    r1 = requests.get(
        f"{TELEGRAM_API}/getFile",
        params={"file_id": file_id},
        timeout=15,
    )
    r1.raise_for_status()
    file_path = r1.json()["result"]["file_path"]
    # 2) baixa bytes direto (sem salvar em disco)
    r2 = requests.get(f"{TELEGRAM_FILE_API}/{file_path}", timeout=60)
    r2.raise_for_status()
    return r2.content


# -------------------------------------------------------------------
# Funções de fluxo (como no 1º programa)
# -------------------------------------------------------------------
def get_financing_message(financiamento_status, tipo_escolhido):
    if financiamento_status is True:
        if tipo_escolhido:
            return (f"Perfeito ({tipo_escolhido.capitalize()}). "
                    "Um de nossos especialistas entrará em contato para falar sobre as opções de crédito.")
        return "Interesse em financiamento registrado. Um especialista entrará em contato."
    return "Pagamento finalizado."


def processar_resposta_financiamento(chat_id, resposta_sim):
    if resposta_sim:
        tg_send_message(chat_id, "Ótimo! Esse financiamento seria para automóvel ou imóvel?")
    else:
        tg_send_message(chat_id, get_financing_message(False, None))


def processar_tipo_financiamento(chat_id, tipo_escolhido):
    t = (tipo_escolhido or "").lower().strip()
    tipo_normalizado = "desconhecido"
    if t in ("automovel", "automóvel", "carro"):
        tipo_normalizado = "Automóvel"
    elif t in ("imovel", "imóvel", "casa", "apto", "apartamento"):
        tipo_normalizado = "Imóvel"

    if tipo_normalizado == "desconhecido":
        tg_send_message(chat_id, f"Não entendi a opção '{tipo_escolhido}', mas registrei seu interesse. "
                                 "Um especialista entrará em contato.")
    else:
        tg_send_message(chat_id, get_financing_message(True, tipo_normalizado))


# -------------------------------------------------------------------
# Processar arquivo: baixa do Telegram → base64 → publica no Kafka
# -------------------------------------------------------------------
def processar_arquivo(file_id: str, chat_id: int, attachment_type: str, source_id: int) -> None:
    """
    attachment_type: "image" para photos, "document" para documentos (pdf, etc).
    """
    blob = tg_get_file_bytes(file_id)
    b64 = base64.b64encode(blob).decode("ascii")  # sem quebras e com padding correto
    publisher.publish(
        source_id=source_id,
        attachment_type=attachment_type,
        attachment_data=b64,
    )
    tg_send_message(chat_id, "✅ Arquivo recebido e enviado para processamento.")


# -------------------------------------------------------------------
# WEBHOOK TELEGRAM (combina com o 1º programa + envio em B64)
# -------------------------------------------------------------------
@app.route("/telegram-webhook", methods=["POST"])
def telegram_webhook():
    update = request.json or {}
    msg = update.get("message") or {}
    chat = msg.get("chat") or {}
    chat_id = chat.get("id")
    source_id = int((msg.get("from") or {}).get("id", 0))
    if not chat_id:
        return jsonify(success=True)

    state = user_states.get(chat_id)

    # ---------------- Nível 1: aguardando SIM/NÃO ----------------
    if state == "awaiting_finance_reply" and "text" in msg:
        text = (msg["text"] or "").lower().strip()
        resposta_foi_sim = text in ("sim", "s", "ss", "y", "yes")
        processar_resposta_financiamento(chat_id, resposta_foi_sim)
        if resposta_foi_sim:
            user_states[chat_id] = "awaiting_property_type"
        else:
            user_states.pop(chat_id, None)
        return jsonify(success=True)

    # --------------- Nível 2: aguardando tipo (auto/imóvel) ------
    if state == "awaiting_property_type" and "text" in msg:
        tipo_escolhido = (msg["text"] or "").strip()
        processar_tipo_financiamento(chat_id, tipo_escolhido)
        user_states.pop(chat_id, None)
        return jsonify(success=True)

    # ---------------------- Sem estado em andamento ----------------
    # Comando de texto
    if "text" in msg:
        text = (msg["text"] or "").strip()
        if text == "/financiamento":
            tg_send_message(chat_id, "Gostaria de fazer um financiamento? (Responda 'sim' ou 'não')")
            user_states[chat_id] = "awaiting_finance_reply"
        else:
            tg_send_message(chat_id, "Recebi o texto. Envie uma foto ou um PDF, ou digite /financiamento.")
        return jsonify(success=True)

    # Foto (pega a maior)
    if "photo" in msg:
        if state:
            tg_send_message(chat_id, "Por favor, termine a conversa anterior antes de enviar um novo arquivo.")
            return jsonify(success=True)
        file_id = msg["photo"][-1]["file_id"]
        try:
            processar_arquivo(file_id, source_id, attachment_type="image",
                              source_id=source_id)
        except Exception as e:
            tg_send_message(chat_id, f"❌ Erro ao processar a foto: {e}")
        return jsonify(success=True)

    # Documento (pdf, etc.)
    if "document" in msg:
        if state:
            tg_send_message(chat_id, "Por favor, termine a conversa anterior antes de enviar um novo arquivo.")
            return jsonify(success=True)
        file_id = msg["document"]["file_id"]
        try:
            processar_arquivo(file_id, source_id, attachment_type="document",
                              source_id=source_id)
        except Exception as e:
            tg_send_message(chat_id, f"❌ Erro ao processar o documento: {e}")
        return jsonify(success=True)

    # Mensagens sem texto/foto/documento
    return jsonify(success=True)


# -------------------------------------------------------------------
# API para iniciar fluxo (como no 1º programa)
# -------------------------------------------------------------------
@app.route("/api/processar", methods=["POST"])
def processar_dados():
    data = request.json or {}
    source_id = data.get("source_id")
    agent_analysis = data.get("agent_analysis")
    trigger_recommendation = data.get("trigger_recommendation")
    financiamento = data.get("financiamento", False)
    chat_id = source_id

    if trigger_recommendation is True:
        if not source_id or not agent_analysis:
            return jsonify({"erro": "source_id e agent_analysis são obrigatórios quando trigger é true"}), 400

    if trigger_recommendation is True:
        if not chat_id:
            return jsonify({"erro": "chat_id é obrigatório quando financiamento é true"}), 400
        tg_send_message(chat_id, "Olá! Identificamos uma oportunidade. Esse financiamento seria para automóvel ou imóvel?")
        user_states[chat_id] = "awaiting_property_type"
        return jsonify({"status": "sucesso",
                        "mensagem": f"Fluxo de financiamento iniciado no chat {chat_id}."}), 200

    # financiamento=False → notificação simples
    mensagem_resposta = get_financing_message(False, None)
    if chat_id:
        tg_send_message(chat_id, f"Olá! Uma atualização da API: {mensagem_resposta}")
    return jsonify({"status": "sucesso",
                    "mensagem": mensagem_resposta,
                    "dados_processados": data}), 200


# -------------------------------------------------------------------
# API para enviar mensagem manualmente
# -------------------------------------------------------------------
@app.route("/api/send_message", methods=["POST"])
def api_send_message():
    data = request.json or {}
    chat_id = data.get("chat_id")  # (corrigido: antes pegava source_id por engano)
    text = data.get("text")
    if not chat_id or not text:
        return jsonify({"erro": "chat_id e text são obrigatórios"}), 400
    try:
        tg_send_message(chat_id, text)
        return jsonify({"status": "ok", "mensagem": "enviada"}), 200
    except Exception as e:
        return jsonify({"erro": str(e)}), 500


# -------------------------------------------------------------------
# Healthcheck
# -------------------------------------------------------------------
@app.route("/health", methods=["GET"])
def health():
    return jsonify(ok=True)


# -------------------------------------------------------------------
# Entry-point
# -------------------------------------------------------------------
if __name__ == "__main__":
    # Ex.: BOT_TOKEN=xxx KAFKA_BROKER_URL=kafka:29092 TOPIC_OUT_NAME=btg.raw python api/main.py
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "3000")), debug=True)
