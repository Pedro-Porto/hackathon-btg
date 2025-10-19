import os
import sys
import requests

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core.kafka import KafkaJSON

KAFKA_BROKER = os.getenv("KAFKA_BROKER_URL", "kafka:9092")
INPUT_TOPIC   = os.getenv("INPUT_TOPIC", "btg.composed")
GROUP_ID      = os.getenv("GROUP_ID", "btg-send-worker-group")
API_URL       = os.getenv("API_URL", "http://api:3000").rstrip("/")

def on_msg(topic: str, data: dict):
    # espera: { "source_id": int, "offer_message": str, "timestamp": int }
    source_id = data.get("source_id")
    text = data.get("offer_message")

    if not source_id or not text:
        print("mensagem inválida, faltando source_id ou offer_message:", data)
        return

    payload = {"source_id": source_id, "text": text}
    try:
        r = requests.post(f"{API_URL}/api/send_message", json=payload, timeout=10)
        if r.status_code == 200:
            print(f"enviada para chat_id={source_id}")
        else:
            print(f"erro HTTP {r.status_code}: {r.text}")
    except Exception as e:
        print(f"falha ao enviar requisição: {e}")

def main():
    print(f"consumindo de {INPUT_TOPIC} @ {KAFKA_BROKER} → POST {API_URL}/api/send_message")
    k = KafkaJSON(broker=KAFKA_BROKER, group_id=GROUP_ID)
    k.subscribe(INPUT_TOPIC)
    try:
        k.loop(on_msg)
    except KeyboardInterrupt:
        print("\nencerrado")
    finally:
        if hasattr(k, "close"):
            k.close()

if __name__ == "__main__":
    main()
