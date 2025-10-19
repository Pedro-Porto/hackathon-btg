# file: ingest/enrich_worker.py
import os
import sys
from typing import Any, Dict

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.kafka import KafkaJSON
from core.database import Database
from database_enricher import DatabaseEnricher
from message_enricher import MessageEnricher


def send_json(k: KafkaJSON, topic: str, obj: Dict[str, Any]) -> None:
    """Compatível com clientes que expõem send(...) ou publish(...)."""
    if hasattr(k, "send"):
        k.send(topic, obj)
    elif hasattr(k, "publish"):
        k.publish(topic, obj)
    else:
        raise AttributeError("KafkaJSON não possui 'send' nem 'publish'.")


class EnrichWorker:
    def __init__(
        self,
        kafka_broker: str,
        input_topic: str,
        output_topic: str,
        group_id: str,
        database_enricher: DatabaseEnricher,
    ):
        self.kafka_client = KafkaJSON(broker=kafka_broker, group_id=group_id)
        self.input_topic = input_topic
        self.output_topic = output_topic
        self.database_enricher = database_enricher
        self.message_enricher = MessageEnricher(database_enricher)
        print(f"✅ EnrichWorker pronto. IN={self.input_topic} OUT={self.output_topic} BROKER={kafka_broker} GROUP={group_id}")

    def process_message(self, topic: str, data: Dict[str, Any]):
        print(f"[MSG] recebido de '{topic}': {data}")
        try:
            enriched = self.message_enricher.enrich(data)
            if enriched:
                send_json(self.kafka_client, self.output_topic, enriched)
                print(f"[OK] enviado para '{self.output_topic}': {enriched}")
            else:
                print("[SKIP] não foi possível enriquecer a mensagem.")
        except Exception as e:
            print(f"[ERRO] process_message: {e}")

    def start(self):
        print("▶️  Iniciando EnrichWorker...")
        print(f"→ Subscribing: {self.input_topic}")
        self.kafka_client.subscribe(self.input_topic)
        try:
            self.kafka_client.loop(self.process_message)
        except KeyboardInterrupt:
            print("\n⛔ Encerrando por KeyboardInterrupt...")
        finally:
            self.database_enricher.close()
            print("🏁 Worker finalizado.")


def main():
    KAFKA_BROKER = os.getenv("KAFKA_BROKER_URL", "localhost:29092")
    INPUT_TOPIC = os.getenv("INPUT_TOPIC", "btg.verified")
    OUTPUT_TOPIC = os.getenv("OUTPUT_TOPIC", "btg.enriched")
    GROUP_ID = os.getenv("GROUP_ID", "btg-enrich-worker-group")

    DB_CONFIG = {
        "host": os.getenv("PGHOST", "localhost"),
        "port": int(os.getenv("PGPORT", "5433")),
        "database": os.getenv("PGDATABASE", "postgres"),
        "user": os.getenv("PGUSER", "postgres"),
        "password": os.getenv("PGPASSWORD", "postgres"),
    }

    print("🔌 Inicializando Database...")
    db = Database(**DB_CONFIG)

    print("🧠 Inicializando DatabaseEnricher...")
    db_enricher = DatabaseEnricher(db)

    worker = EnrichWorker(
        kafka_broker=KAFKA_BROKER,
        input_topic=INPUT_TOPIC,
        output_topic=OUTPUT_TOPIC,
        group_id=GROUP_ID,
        database_enricher=db_enricher,
    )
    worker.start()


if __name__ == "__main__":
    main()
