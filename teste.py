import requests
import base64
from flask import Flask, request, jsonify
import os

BOT_TOKEN = "7533069936:AAGrIFseMpWotMurF--EdP4Ru8kLJuCig5U" 

app = Flask(__name__) 
PASTA_DOWNLOADS = "downloads" 

# Dicionário de "memória" para estados da conversa
user_states = {}

# ===================================================================
# ROTA 1: WEBHOOK DO TELEGRAM (Sem alterações)
# ===================================================================
@app.route('/telegram-webhook', methods=['POST'])
def receive_webhook():
    update_data = request.json
    print("Nova mensagem")
    print(update_data) 
    
    if 'message' in update_data:
        message = update_data['message']
        chat_id = message['chat']['id']
        current_state = user_states.get(chat_id) 

        # --- ETAPA 1: VERIFICAR SE ESTAMOS NO MEIO DE UMA CONVERSA ---
        
        # --- NÍVEL 1: Usuário está respondendo "sim" ou "não" ---
        if current_state == "awaiting_finance_reply" and 'text' in message:
            text = message['text'].lower().strip()
            resposta_foi_sim = text in ['sim', 's', 'ss', 'y', 'yes']
            
            processar_resposta_financiamento(chat_id, resposta_foi_sim)
            
            if resposta_foi_sim:
                user_states[chat_id] = "awaiting_property_type" 
            else:
                if chat_id in user_states:
                    del user_states[chat_id]
            
            return jsonify(success=True)

        # --- NÍVEL 2: Usuário está respondendo "automóvel" ou "imóvel" ---
        # (Esta é a parte que a API agora vai pular direto para)
        elif current_state == "awaiting_property_type" and 'text' in message:
            tipo_escolhido = message['text'].lower().strip()
            processar_tipo_financiamento(chat_id, tipo_escolhido)
            
            if chat_id in user_states:
                del user_states[chat_id]
            
            return jsonify(success=True) 

        # --- ETAPA 2: SE NÃO ESTIVER EM UMA CONVERSA, PROCESSAR NORMALMENTE ---
        
        if 'text' in message:
            text = message['text'].strip() 

            if text == "/financiamento":
                print(f"Chat {chat_id} iniciou o fluxo de financiamento.")
                enviar_mensagem_telegram(chat_id, "Gostaria de fazer um financiamento? (Responda 'sim' ou 'não')")
                user_states[chat_id] = "awaiting_finance_reply"
            
            else:
                print(f"Mensagem de TEXTO recebida de {chat_id}")
                enviar_mensagem_telegram(chat_id, "Recebi o texto. Envie uma foto ou um PDF para conversão, ou digite /financiamento para iniciar.")

        elif 'photo' in message:
            if current_state:
                enviar_mensagem_telegram(chat_id, "Por favor, termine a conversa anterior antes de enviar um novo arquivo.")
                return jsonify(success=True)
                
            print(f"Mensagem de FOTO recebida de {chat_id}")
            enviar_mensagem_telegram(chat_id, "Recebi foto, processando...")
            
            file_id = message['photo'][-1]['file_id']
            processar_arquivo(file_id, chat_id, "Foto") 

        elif 'document' in message:
            if current_state:
                enviar_mensagem_telegram(chat_id, "Por favor, termine a conversa anterior antes de enviar um novo arquivo.")
                return jsonify(success=True)
                
            print(f"Mensagem de DOCUMENTO recebida de {chat_id}")
            
            file_id = message['document']['file_id']
            file_name = message['document'].get('file_name', 'arquivo')
            
            enviar_mensagem_telegram(chat_id, f"Recebi o documento '{file_name}', processando...")
            
            processar_arquivo(file_id, chat_id, file_name)

    return jsonify(success=True)

# ===================================================================
# ROTA 2: API (MODIFICADA para INICIAR a conversa no chat)
# ===================================================================
@app.route('/api/processar', methods=['POST'])
def processar_dados():
    data = request.json
    
    if not data:
        return jsonify({"erro": "Nenhum dado enviado no body"}), 400
    
    # --- ETAPA 1: Extrair dados ---
    source_id = data.get('source_id')
    agent_analysis = data.get('agent_analysis')
    trigger_recommendation = data.get('trigger_recommendation')
    financiamento = data.get('financiamento', False) 
    chat_id_para_notificar = data.get('chat_id')

    # --- ETAPA 2: Validação (Opcional, mas bom) ---
    if trigger_recommendation is True:
        print("LOG (API): Trigger ATIVADO.")
        if not source_id or not agent_analysis:
             return jsonify({"erro": "source_id e agent_analysis são obrigatórios quando trigger é true"}), 400
        print("LOG (API): Validação OK.")
    else:
        print("LOG (API): Trigger INATIVO.")
        
    # --- ETAPA 3: Lógica de Ação (A GRANDE MUDANÇA) ---
    
    if financiamento is True:
        # Se financiamento for true, A API DEVE INICIAR A CONVERSA
        
        if not chat_id_para_notificar:
            # Precisa saber PARA QUEM perguntar
            return jsonify({"erro": "chat_id é obrigatório quando financiamento é true para iniciar a conversa"}), 400
        
        print(f"LOG (API): Iniciando fluxo (Auto/Imóvel) para chat {chat_id_para_notificar}")
        
        # 1. Faz a pergunta no chat (pulando o "sim/não")
        enviar_mensagem_telegram(chat_id_para_notificar, "Olá! Identificamos uma oportunidade. Esse financiamento seria para automóvel ou imóvel?")
        
        # 2. Define o estado do usuário (para que o bot saiba o que esperar)
        user_states[chat_id_para_notificar] = "awaiting_property_type"
        
        # 3. Retorna a resposta para a API
        return jsonify({
            "status": "sucesso",
            "mensagem": f"Fluxo de financiamento (automóvel/imóvel) iniciado no chat {chat_id_para_notificar}."
        }), 200
    
    else: 
        # Se financiamento for False, apenas envia a notificação final
        mensagem_resposta = get_financing_message(False, None) # "Pagamento finalizado."
        
        if chat_id_para_notificar:
            # Se um chat_id foi dado, envia a notificação
            enviar_mensagem_telegram(chat_id_para_notificar, f"Olá! Uma atualização da API: {mensagem_resposta}")
        
        # Retorna a resposta para a API
        return jsonify({
            "status": "sucesso",
            "mensagem": mensagem_resposta,
            "dados_processados": data
        }), 200

# ===================================================================
# FUNÇÕES AUXILIARES (Lógica do Bot e Arquivos) - (Sem alterações)
# ===================================================================

def get_financing_message(financiamento_status, tipo_escolhido):
    if financiamento_status is True:
        if tipo_escolhido:
            return f"Perfeito ({tipo_escolhido.capitalize()}). Um de nossos especialistas entrará em contato para falar sobre as opções de crédito."
        else:
            return "Interesse em financiamento registrado. Um especialista entrará em contato."
    else:
        return "Pagamento finalizado."

def processar_resposta_financiamento(chat_id, resposta_sim):
    if resposta_sim:
        enviar_mensagem_telegram(chat_id, "Ótimo! Esse financiamento seria para automóvel ou imóvel?")
    else:
        mensagem_final = get_financing_message(False, None)
        enviar_mensagem_telegram(chat_id, mensagem_final)

def processar_tipo_financiamento(chat_id, tipo_escolhido):
    tipo_normalizado = "desconhecido"
    
    if tipo_escolhido in ['automovel', 'automóvel', 'carro']:
        print(f"Chat {chat_id} escolheu financiamento de AUTOMÓVEL.")
        tipo_normalizado = "Automóvel"
        
    elif tipo_escolhido in ['imovel', 'imóvel', 'casa', 'apto', 'apartamento']:
        print(f"Chat {chat_id} escolheu financiamento de IMÓVEL.")
        tipo_normalizado = "Imóvel"
    
    mensagem_final = get_financing_message(True, tipo_normalizado)
    
    if tipo_normalizado == "desconhecido":
         enviar_mensagem_telegram(chat_id, f"Não entendi a opção '{tipo_escolhido}', mas registrei seu interesse. Um especialista entrará em contato.")
    else:
        enviar_mensagem_telegram(chat_id, mensagem_final)


def processar_arquivo(file_id, chat_id, tipo_arquivo):
    try:
        url_passo_a = f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}"
        response_a = requests.get(url_passo_a)
        file_path = response_a.json()['result']['file_path']
        
        url_passo_b = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
        response_b = requests.get(url_passo_b)
        image_bytes = response_b.content 
        
        nome_arquivo_original = os.path.basename(file_path)
        print(f"Arquivo '{nome_arquivo_original}' baixado ({len(image_bytes)} bytes)")

        if not os.path.exists(PASTA_DOWNLOADS):
            os.makedirs(PASTA_DOWNLOADS)
        
        caminho_para_salvar = os.path.join(PASTA_DOWNLOADS, nome_arquivo_original)

        with open(caminho_para_salvar, "wb") as f:
            f.write(image_bytes)
        
        print(f"Arquivo salvo com sucesso em: {caminho_para_salvar}")
        
        base64_bytes = base64.b64encode(image_bytes)
        base64_string = base64_bytes.decode('utf-8')
        
        mensagem_sucesso = f"Sucesso! O arquivo '{tipo_arquivo}' foi salvo em '{caminho_para_salvar}'. A Base64 começa com: {base64_string[:50]}..."
        enviar_mensagem_telegram(chat_id, mensagem_sucesso)

    except Exception as e:
        print(f"ERRO durante o processamento do arquivo: {e}")
        mensagem_erro = f"Desculpe, ocorreu um erro ao processar seu arquivo: '{tipo_arquivo}'."
        enviar_mensagem_telegram(chat_id, mensagem_erro)

def enviar_mensagem_telegram(chat_id, texto):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": texto,
    }
    try:
        requests.post(url, json=payload)
        print(f"Mensagem de resposta enviada para {chat_id}.")
    except Exception as e:
        print(f"ERRO ao enviar mensagem de resposta: {e}")

# ===================================================================
# INÍCIO DO SERVIDOR
# ===================================================================
if __name__ == '__main__':
    print("Iniciando o servidor Flask (com rotas de API e Telegram)...")
    app.run(port=5000, debug=True)