# publicador_anexo.py

import time
import json
from kafka_lib import KafkaJSON  # Importando sua biblioteca

# --- CONFIGURAÇÕES GLOBAIS ---
KAFKA_BROKER_URL = "localhost:29092"
TOPIC_NAME = "btg.raw"

# --- FUNÇÃO 1: Autentica no Kafka ---
def autentica_no_kafka(broker_url: str) -> KafkaJSON | None:
    """
    Cria uma conexão com o Kafka utilizando a biblioteca KafkaJSON.

    Args:
        broker_url: O endereço do servidor Kafka (ex: 'localhost:29092').

    Returns:
        Uma instância do cliente KafkaJSON em caso de sucesso, ou None se ocorrer um erro.
    """
    print(f"Tentando conectar ao broker Kafka em {broker_url}...")
    try:
        cliente_kafka = KafkaJSON(broker=broker_url)
        print("Conexão com o Kafka estabelecida com sucesso!")
        return cliente_kafka
    except Exception as e:
        print(f"Erro: Não foi possível conectar ao Kafka. Detalhes: {e}")
        return None

# --- FUNÇÃO 2: Recebe dados do anexo e publica a mensagem ---
def publicar_mensagem_com_anexo(
    cliente_kafka: KafkaJSON, 
    source_id: int, 
    attachment_type: str,
    attachment_data: str
) -> None:
    """
    Cria o objeto da mensagem com os dados do anexo e o publica no tópico Kafka.
    A mensagem é enviada sem uma chave (key).

    Args:
        cliente_kafka: A instância do cliente Kafka já conectada.
        source_id: O identificador de origem.
        attachment_type: O tipo de anexo (ex: 'image').
        attachment_data: Os dados do anexo, geralmente em base64.
    """
    if not cliente_kafka:
        print("Erro: Cliente Kafka não inicializado. Mensagem não pode ser publicada.")
        return

    # 1. Monta o payload (o objeto da mensagem) como um dicionário Python
    mensagem_payload = {
        "source_id": source_id,
        "attachment_type": attachment_type,
        "attachment_data": attachment_data,
        "timestamp": int(time.time() * 1000)  # <--- ALTERADO PARA MILISSEGUNDOS
    }
    
    print(f"Publicando no tópico '{TOPIC_NAME}': {json.dumps(mensagem_payload)}")

    # 2. Usa o método .send() da sua biblioteca para publicar
    try:
        cliente_kafka.send(TOPIC_NAME, mensagem_payload)
        print("Mensagem publicada com sucesso!")
    except Exception as e:
        print(f"Ocorreu um erro ao tentar publicar a mensagem: {e}")


# --- BLOCO DE EXECUÇÃO PRINCIPAL (EXEMPLO DE USO) ---
if __name__ == "__main__":
    # Passo 1: Autenticar e obter o cliente Kafka
    meu_cliente_kafka = autentica_no_kafka(KAFKA_BROKER_URL)

    # Verifica se a conexão foi bem-sucedida
    if meu_cliente_kafka:
        # Passo 2: Usar os dados de exemplo
        exemplo_source_id = 1
        exemplo_attachment_type = "image"
        exemplo_attachment_data = "A"

        publicar_mensagem_com_anexo(
            meu_cliente_kafka, 
            exemplo_source_id, 
            exemplo_attachment_type, 
            exemplo_attachment_data
        )

        # Passo 3: Fechar a conexão ao final do uso
        meu_cliente_kafka.close()
        print("\nCliente Kafka fechado.")
