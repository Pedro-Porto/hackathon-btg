# file: api/main.py
import os
import sys
import base64
import requests
from flask import Flask, request, jsonify

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from ingest import RawPublisher  
from core.kafka import KafkaJSON


BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("Defina BOT_TOKEN no ambiente.")

TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"
TELEGRAM_FILE_API = f"https://api.telegram.org/file/bot{BOT_TOKEN}"

app = Flask(__name__)
publisher = RawPublisher(auto_connect=True)
kafka = KafkaJSON(broker=os.getenv("KAFKA_BROKER_URL", "localhost:29092"), group_id="btg-api-group")

user_states = {}          
processed_callbacks = set()
processing_chats = set()
verify_state = {}


def extract_ids_from_update(update: dict):
    """Extrai chat_id (Telegram) e source_id (usuário real)"""
    msg = update.get("message") or {}
    cb = update.get("callback_query") or {}
    msg_from = (msg.get("from") or {}) if msg else (cb.get("from") or {})
    message = msg or (cb.get("message") or {})
    chat_id = (message.get("chat") or {}).get("id")
    source_id = msg_from.get("id")
    return chat_id, source_id


def tg_send_message(chat_id: int, text: str) -> None:
    try:
        requests.post(f"{TELEGRAM_API}/sendMessage",
                      json={"chat_id": chat_id, "text": text}, timeout=15)
    except Exception:
        pass

def tg_send_message_with_keyboard(chat_id: int, text: str, keyboard: dict) -> None:
    try:
        requests.post(f"{TELEGRAM_API}/sendMessage",
                      json={"chat_id": chat_id, "text": text, "reply_markup": keyboard}, timeout=15)
    except Exception:
        pass

def tg_edit_message_keyboard(chat_id: int, message_id: int, text: str) -> None:
    try:
        requests.post(f"{TELEGRAM_API}/editMessageText",
                      json={
                          "chat_id": chat_id,
                          "message_id": message_id,
                          "text": text,
                          "reply_markup": {"inline_keyboard": []}
                      }, timeout=15)
    except Exception:
        pass

def tg_disable_keyboard_immediately(chat_id: int, message_id: int) -> None:
    try:
        requests.post(f"{TELEGRAM_API}/editMessageReplyMarkup",
                      json={"chat_id": chat_id, "message_id": message_id,
                            "reply_markup": {"inline_keyboard": []}}, timeout=15)
    except Exception:
        pass

def tg_get_file_bytes(file_id: str) -> bytes:
    r1 = requests.get(f"{TELEGRAM_API}/getFile", params={"file_id": file_id}, timeout=15)
    r1.raise_for_status()
    file_path = r1.json()["result"]["file_path"]
    r2 = requests.get(f"{TELEGRAM_FILE_API}/{file_path}", timeout=60)
    r2.raise_for_status()
    return r2.content

def get_financing_message(financiamento_status, tipo_escolhido):
    if financiamento_status is True:
        if tipo_escolhido:
            return (f"Perfeito ({tipo_escolhido.capitalize()}). "
                    "Um de nossos especialistas entrará em contato para falar sobre as opções de crédito.")
        return "Interesse em financiamento registrado. Um especialista entrará em contato."
    return "Pagamento finalizado."

def processar_resposta_financiamento(chat_id, source_id, resposta_sim):
    if resposta_sim:
        keyboard = {
            "inline_keyboard": [[
                {"text": "🚗 Automóvel", "callback_data": "tipo_automovel"},
                {"text": "🏠 Imóvel", "callback_data": "tipo_imovel"}
            ]]
        }
        tg_send_message_with_keyboard(chat_id, "Ótimo! Esse financiamento seria para automóvel ou imóvel?", keyboard)
        user_states[source_id] = "awaiting_property_type"
    else:
        tg_send_message(chat_id, get_financing_message(False, None))
        user_states.pop(source_id, None)

def processar_tipo_financiamento(chat_id, source_id, tipo_escolhido):
    if tipo_escolhido == "tipo_automovel":
        tipo_normalizado = "Automóvel"
    elif tipo_escolhido == "tipo_imovel":
        tipo_normalizado = "Imóvel"
    else:
        t = (tipo_escolhido or "").lower().strip()
        tipo_normalizado = None
        if t in ("automovel", "automóvel", "carro"):
            tipo_normalizado = "Automóvel"
        elif t in ("imovel", "imóvel", "casa", "apto", "apartamento"):
            tipo_normalizado = "Imóvel"

    to_eng = {
        "Automóvel": "automobile",
        "Imóvel": "property"
    }
    
    verify_state[source_id]['financing_type'] = to_eng[tipo_normalizado]

    if not tipo_normalizado:
        tg_send_message(chat_id, f"Não entendi a opção '{tipo_escolhido}'. Use os botões.")
        return

    user_states[source_id] = f"tipo_escolhido_{tipo_normalizado}"
    tg_send_message(chat_id,
        f"Perfeito! Para {tipo_normalizado}, qual o valor aproximado que você gostaria de financiar? "
        "(Digite apenas o número, ex: 50000)"
    )

def processar_escolha_valor(chat_id, source_id, valor_texto):
    try:
        valor_limpo = ''.join(c for c in valor_texto if c.isdigit() or c in '.,')
        if not valor_limpo:
            tg_send_message(chat_id, "❌ Por favor, digite um valor numérico válido. Ex.: 50000 ou 50.000")
            return
        valor_limpo = valor_limpo.replace(',', '.')
        valor_numerico = float(valor_limpo)
        if valor_numerico <= 0:
            tg_send_message(chat_id, "❌ O valor deve ser maior que zero. Tente novamente.")
            return
    except ValueError:
        tg_send_message(chat_id, "❌ Por favor, digite um valor numérico válido. Ex.: 50000 ou 50.000")
        return

    estado_anterior = user_states.get(source_id, "")
    tipo_escolhido = "financiamento"
    if estado_anterior.startswith("tipo_escolhido_"):
        tipo_escolhido = estado_anterior.replace("tipo_escolhido_", "")

    valor_formatado = f"R$ {valor_numerico:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    mensagem_final = (f"Perfeito! Registramos seu interesse em financiamento para {tipo_escolhido} "
                      f"no valor de {valor_formatado}. "
                      "Um de nossos especialistas entrará em contato para falar sobre as opções de crédito.")
    user_varify_state = verify_state.get(source_id, {})
    if not user_varify_state:
        tg_send_message(chat_id, "❌ Ocorreu um erro interno. Por favor, inicie o processo novamente.")
        user_states.pop(source_id, None)
        return
    
    kafka.send('btg.verified', {
        "source_id": source_id,
        "agent_analysis": user_varify_state.get("agent_analysis"),
        "financing_info": {
            "type": user_varify_state.get("financing_type"),
            "value": valor_numerico
        },
        "timestamp": 0
    })
    # tg_send_message(chat_id, mensagem_final)
    user_states.pop(source_id, None)


def processar_arquivo(file_id: str, chat_id: int, source_id: int, attachment_type: str) -> None:
    blob = tg_get_file_bytes(file_id)
    b64 = base64.b64encode(blob).decode("ascii")
    publisher.publish(
        source_id=source_id,
        attachment_type=attachment_type,
        attachment_data=b64,
    )
    tg_send_message(chat_id, "✅ Arquivo recebido e enviado para processamento.")


@app.route("/telegram-webhook", methods=["POST"])
def telegram_webhook():
    update = request.json or {}
    chat_id, source_id = extract_ids_from_update(update)

    # Callback (cliques)
    if "callback_query" in update:
        callback = update["callback_query"]
        message_id = callback["message"]["message_id"]
        data = callback["data"]
        callback_id = callback["id"]

        if callback_id in processed_callbacks or chat_id in processing_chats:
            requests.post(f"{TELEGRAM_API}/answerCallbackQuery",
                          json={"callback_query_id": callback_id}, timeout=15)
            return jsonify(success=True)

        processed_callbacks.add(callback_id)
        processing_chats.add(chat_id)
        tg_disable_keyboard_immediately(chat_id, message_id)

        if data in ("financiamento_sim", "financiamento_nao"):
            resposta_sim = (data == "financiamento_sim")
            tg_edit_message_keyboard(chat_id, message_id, f"Resposta: {'✅ Sim' if resposta_sim else '❌ Não'}")
            processar_resposta_financiamento(chat_id, source_id, resposta_sim)
        elif data in ("tipo_automovel", "tipo_imovel"):
            tipo_label = "Automóvel" if data == "tipo_automovel" else "Imóvel"
            tg_edit_message_keyboard(chat_id, message_id, f"✅ Escolhido: {tipo_label}")
            processar_tipo_financiamento(chat_id, source_id, data)

        processing_chats.discard(chat_id)
        requests.post(f"{TELEGRAM_API}/answerCallbackQuery",
                      json={"callback_query_id": callback_id}, timeout=15)
        return jsonify(success=True)

    msg = update.get("message") or {}
    if not chat_id:
        return jsonify(success=True)

    state = user_states.get(source_id)

    if state and state.startswith("tipo_escolhido_") and "text" in msg:
        processar_escolha_valor(chat_id, source_id, (msg["text"] or "").strip())
        return jsonify(success=True)

    if "text" in msg and not (state and state.startswith("tipo_escolhido_")):
        text = (msg["text"] or "").strip()
        if text == "/financiamento":
            keyboard = {"inline_keyboard": [[
                {"text": "✅ Sim", "callback_data": "financiamento_sim"},
                {"text": "❌ Não", "callback_data": "financiamento_nao"}]]}
            tg_send_message_with_keyboard(chat_id, "Gostaria de fazer um financiamento?", keyboard)
            user_states[source_id] = "awaiting_finance_reply"
        else:
            tg_send_message(chat_id, "Recebi o texto. Envie uma foto ou um PDF, ou digite /financiamento.")
        return jsonify(success=True)

    if "photo" in msg:
        if state:
            tg_send_message(chat_id, "Por favor, termine a conversa anterior antes de enviar um novo arquivo.")
            return jsonify(success=True)
        file_id = msg["photo"][-1]["file_id"]
        processar_arquivo(file_id, chat_id, source_id, "image")
        return jsonify(success=True)

    if "document" in msg:
        if state:
            tg_send_message(chat_id, "Por favor, termine a conversa anterior antes de enviar um novo arquivo.")
            return jsonify(success=True)
        file_id = msg["document"]["file_id"]
        processar_arquivo(file_id, chat_id, source_id, "document")
        return jsonify(success=True)

    return jsonify(success=True)


@app.route("/api/processar", methods=["POST"])
def processar_dados():
    data = request.json or {}
    source_id = data.get("source_id")
    agent_analysis = data.get("agent_analysis")
    trigger_recommendation = data.get("trigger_recommendation")
    chat_id = source_id
    verify_state[source_id] = {
        "agent_analysis": agent_analysis,
        "trigger_recommendation": trigger_recommendation
    }

    if trigger_recommendation:
        if not source_id or not agent_analysis:
            return jsonify({"erro": "source_id e agent_analysis são obrigatórios"}), 400
        keyboard = {"inline_keyboard": [[
            {"text": "🚗 Automóvel", "callback_data": "tipo_automovel"},
            {"text": "🏠 Imóvel", "callback_data": "tipo_imovel"}]]}
        tg_send_message_with_keyboard(chat_id,
            "Olá! Identificamos uma oportunidade. Esse financiamento seria para automóvel ou imóvel?", keyboard)
        user_states[source_id] = "awaiting_property_type"
        return jsonify({"status": "sucesso",
                        "mensagem": f"Fluxo iniciado para source_id {source_id}"}), 200

    mensagem_resposta = get_financing_message(False, None)
    if chat_id:
        tg_send_message(chat_id, f"Olá! Uma atualização da API: {mensagem_resposta}")
    return jsonify({"status": "sucesso", "mensagem": mensagem_resposta, "dados_processados": data}), 200


@app.route("/api/send_message", methods=["POST"])
def api_send_message():
    data = request.json or {}
    chat_id = data.get("source_id") or data.get("chat_id")
    text = data.get("text")
    if not chat_id or not text:
        return jsonify({"erro": "source_id (ou chat_id) e text são obrigatórios"}), 400
    tg_send_message(chat_id, text)
    return jsonify({"status": "ok", "mensagem": "enviada"}), 200


@app.route("/health", methods=["GET"])
def health():
    return jsonify(ok=True)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "3000")), debug=True)
