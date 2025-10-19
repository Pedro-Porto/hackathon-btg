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

# Memória simples
user_states = {}            # estado por chat_id
processed_callbacks = set() # callback_query_ids já processados
processing_chats = set()    # chats em processamento (para debouncing)

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

def tg_send_message_with_keyboard(chat_id: int, text: str, keyboard: dict) -> None:
    try:
        requests.post(
            f"{TELEGRAM_API}/sendMessage",
            json={"chat_id": chat_id, "text": text, "reply_markup": keyboard},
            timeout=15,
        )
    except Exception:
        pass

def tg_edit_message_keyboard(chat_id: int, message_id: int, text: str) -> None:
    """Edita a mensagem e remove o teclado inline"""
    try:
        requests.post(
            f"{TELEGRAM_API}/editMessageText",
            json={
                "chat_id": chat_id,
                "message_id": message_id,
                "text": text,
                "reply_markup": {"inline_keyboard": []}
            },
            timeout=15,
        )
    except Exception:
        pass

def tg_disable_keyboard_immediately(chat_id: int, message_id: int) -> None:
    """Remove imediatamente o teclado para evitar cliques múltiplos"""
    try:
        requests.post(
            f"{TELEGRAM_API}/editMessageReplyMarkup",
            json={"chat_id": chat_id, "message_id": message_id, "reply_markup": {"inline_keyboard": []}},
            timeout=15,
        )
    except Exception:
        pass

def tg_get_file_bytes(file_id: str) -> bytes:
    r1 = requests.get(f"{TELEGRAM_API}/getFile", params={"file_id": file_id}, timeout=15)
    r1.raise_for_status()
    file_path = r1.json()["result"]["file_path"]
    r2 = requests.get(f"{TELEGRAM_FILE_API}/{file_path}", timeout=60)
    r2.raise_for_status()
    return r2.content

# -------------------------------------------------------------------
# Funções de fluxo
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
        keyboard = {
            "inline_keyboard": [[
                {"text": "🚗 Automóvel", "callback_data": "tipo_automovel"},
                {"text": "🏠 Imóvel", "callback_data": "tipo_imovel"}
            ]]
        }
        tg_send_message_with_keyboard(chat_id, "Ótimo! Esse financiamento seria para automóvel ou imóvel?", keyboard)
        user_states[chat_id] = "awaiting_property_type"
    else:
        tg_send_message(chat_id, get_financing_message(False, None))
        user_states.pop(chat_id, None)

def processar_tipo_financiamento(chat_id, tipo_escolhido):
    # Mapeia callback_data -> rótulo
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

    if not tipo_normalizado:
        tg_send_message(chat_id, f"Não entendi a opção '{tipo_escolhido}'. Use os botões.")
        return

    # Guarda estado para a próxima etapa (valor)
    user_states[chat_id] = f"tipo_escolhido_{tipo_normalizado}"

    # Pergunta o valor (entrada de texto)
    tg_send_message(
        chat_id,
        f"Perfeito! Para {tipo_normalizado}, qual o valor aproximado que você gostaria de financiar? "
        "(Digite apenas o número, ex: 50000)"
    )

def processar_escolha_valor(chat_id, valor_texto):
    """Processa a escolha do valor (entrada de texto)"""
    try:
        # Mantém apenas dígitos, ponto e vírgula
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

    # Obtém o tipo escolhido no estado
    estado_anterior = user_states.get(chat_id, "")
    tipo_escolhido = "financiamento"
    if estado_anterior.startswith("tipo_escolhido_"):
        tipo_escolhido = estado_anterior.replace("tipo_escolhido_", "")

    # Formata valor no padrão brasileiro
    valor_formatado = f"R$ {valor_numerico:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

    mensagem_final = (f"Perfeito! Registramos seu interesse em financiamento para {tipo_escolhido} "
                      f"no valor de {valor_formatado}. "
                      "Um de nossos especialistas entrará em contato para falar sobre as opções de crédito.")
    tg_send_message(chat_id, mensagem_final)

    # Limpa o estado depois de concluir a etapa de valor
    user_states.pop(chat_id, None)

# -------------------------------------------------------------------
# Processar arquivo: baixa do Telegram → base64 → publica no Kafka
# -------------------------------------------------------------------
def processar_arquivo(file_id: str, chat_id: int, attachment_type: str, source_id: int) -> None:
    blob = tg_get_file_bytes(file_id)
    b64 = base64.b64encode(blob).decode("ascii")
    publisher.publish(
        source_id=source_id,
        attachment_type=attachment_type,
        attachment_data=b64,
    )
    tg_send_message(chat_id, "✅ Arquivo recebido e enviado para processamento.")

# -------------------------------------------------------------------
# WEBHOOK TELEGRAM
# -------------------------------------------------------------------
@app.route("/telegram-webhook", methods=["POST"])
def telegram_webhook():
    update = request.json or {}

    # 1) Tratamento de cliques (inline keyboard)
    if "callback_query" in update:
        callback = update["callback_query"]
        chat_id = callback["message"]["chat"]["id"]
        message_id = callback["message"]["message_id"]
        data = callback["data"]
        callback_id = callback["id"]

        # Debounce: callback já processado?
        if callback_id in processed_callbacks:
            try:
                requests.post(f"{TELEGRAM_API}/answerCallbackQuery",
                              json={"callback_query_id": callback_id}, timeout=15)
            except Exception:
                pass
            return jsonify(success=True)

        # Debounce: chat em processamento?
        if chat_id in processing_chats:
            try:
                requests.post(f"{TELEGRAM_API}/answerCallbackQuery",
                              json={"callback_query_id": callback_id}, timeout=15)
            except Exception:
                pass
            return jsonify(success=True)

        processed_callbacks.add(callback_id)
        processing_chats.add(chat_id)

        # Remove imediatamente o teclado para evitar multi-clique
        tg_disable_keyboard_immediately(chat_id, message_id)

        # a) Resposta Sim/Não do financiamento
        if data in ("financiamento_sim", "financiamento_nao"):
            resposta_sim = (data == "financiamento_sim")
            tg_edit_message_keyboard(chat_id, message_id, f"Resposta: {'✅ Sim' if resposta_sim else '❌ Não'}")
            processar_resposta_financiamento(chat_id, resposta_sim)

        # b) Escolha do tipo (Automóvel/Imóvel)
        elif data in ("tipo_automovel", "tipo_imovel"):
            tipo_label = "Automóvel" if data == "tipo_automovel" else "Imóvel"
            tg_edit_message_keyboard(chat_id, message_id, f"✅ Escolhido: {tipo_label}")
            processar_tipo_financiamento(chat_id, data)
            # IMPORTANTE: não apagar estado aqui; ele será usado para capturar o valor de texto
            # (Removido o user_states.pop(chat_id, None) que quebrava o fluxo)

        processing_chats.discard(chat_id)

        # Remove "loading" do botão
        try:
            requests.post(f"{TELEGRAM_API}/answerCallbackQuery",
                          json={"callback_query_id": callback_id}, timeout=15)
        except Exception:
            pass

        return jsonify(success=True)

    # 2) Tratamento de mensagens (texto, foto, documento)
    msg = update.get("message") or {}
    chat = msg.get("chat") or {}
    chat_id = chat.get("id")
    if not chat_id:
        return jsonify(success=True)

    state = user_states.get(chat_id)

    # Nível 3: aguardando valor (entrada de texto)
    if state and state.startswith("tipo_escolhido_") and "text" in msg:
        valor_texto = (msg["text"] or "").strip()
        processar_escolha_valor(chat_id, valor_texto)
        return jsonify(success=True)

    # Sem estado em andamento → comandos de texto
    if "text" in msg and not (state and state.startswith("tipo_escolhido_")):
        text = (msg["text"] or "").strip()
        if text == "/financiamento":
            keyboard = {
                "inline_keyboard": [[
                    {"text": "✅ Sim", "callback_data": "financiamento_sim"},
                    {"text": "❌ Não", "callback_data": "financiamento_nao"}
                ]]
            }
            tg_send_message_with_keyboard(chat_id, "Gostaria de fazer um financiamento?", keyboard)
            user_states[chat_id] = "awaiting_finance_reply"
        else:
            tg_send_message(chat_id, "Recebi o texto. Envie uma foto ou um PDF, ou digite /financiamento.")
        return jsonify(success=True)

    # Foto
    if "photo" in msg:
        if state:
            tg_send_message(chat_id, "Por favor, termine a conversa anterior antes de enviar um novo arquivo.")
            return jsonify(success=True)
        file_id = msg["photo"][-1]["file_id"]
        try:
            processar_arquivo(file_id, chat_id, attachment_type="image", source_id=chat_id)
        except Exception as e:
            tg_send_message(chat_id, f"❌ Erro ao processar a foto: {e}")
        return jsonify(success=True)

    # Documento
    if "document" in msg:
        if state:
            tg_send_message(chat_id, "Por favor, termine a conversa anterior antes de enviar um novo arquivo.")
            return jsonify(success=True)
        file_id = msg["document"]["file_id"]
        try:
            processar_arquivo(file_id, chat_id, attachment_type="document", source_id=chat_id)
        except Exception as e:
            tg_send_message(chat_id, f"❌ Erro ao processar o documento: {e}")
        return jsonify(success=True)

    return jsonify(success=True)

# -------------------------------------------------------------------
# API para iniciar fluxo programaticamente
# -------------------------------------------------------------------
@app.route("/api/processar", methods=["POST"])
def processar_dados():
    data = request.json or {}
    source_id = data.get("source_id")
    agent_analysis = data.get("agent_analysis")
    trigger_recommendation = data.get("trigger_recommendation")
    chat_id = source_id

    if trigger_recommendation is True:
        if not source_id or not agent_analysis:
            return jsonify({"erro": "source_id e agent_analysis são obrigatórios quando trigger é true"}), 400
        if not chat_id:
            return jsonify({"erro": "chat_id é obrigatório quando trigger é true"}), 400

        keyboard = {
            "inline_keyboard": [[
                {"text": "🚗 Automóvel", "callback_data": "tipo_automovel"},
                {"text": "🏠 Imóvel", "callback_data": "tipo_imovel"}
            ]]
        }
        tg_send_message_with_keyboard(
            chat_id,
            "Olá! Identificamos uma oportunidade. Esse financiamento seria para automóvel ou imóvel?",
            keyboard
        )
        user_states[chat_id] = "awaiting_property_type"

        return jsonify({"status": "sucesso",
                        "mensagem": f"Fluxo de financiamento iniciado no chat {chat_id}."}), 200

    # Sem trigger → notificação simples (não envia mensagem se não tiver chat_id)
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
    chat_id = data.get("chat_id")  # Corrigido: usa chat_id mesmo
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
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=True)
