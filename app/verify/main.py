import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import time
import os
from typing import Optional, List

from database import DatabaseManager
from api_client import APIClient
from message_processor import MessageProcessor
from partition_worker import PartitionWorker
from core.llm import LLMWrapper


class WorkerManager:
    def __init__(
        self,
        kafka_bootstrap_servers: str,
        kafka_topic: str,
        kafka_group_id: str,
        database_manager: DatabaseManager,
        api_client: APIClient,
        llm: LLMWrapper,
        worker_count: int = 1,
    ):
        self.kafka_bootstrap_servers = kafka_bootstrap_servers
        self.kafka_topic = kafka_topic
        self.kafka_group_id = kafka_group_id
        self.database_manager = database_manager
        self.api_client = api_client
        self.workers: List[PartitionWorker] = []
        self.message_processor = MessageProcessor(database_manager, api_client, llm)
        self.worker_count = max(1, int(worker_count))

    def start(self):
        try:
            print(f"[Manager] Iniciando {self.worker_count} worker(s) para o tópico '{self.kafka_topic}'...")
            for i in range(self.worker_count):
                w = PartitionWorker(
                    partition=i,
                    kafka_bootstrap_servers=self.kafka_bootstrap_servers,
                    kafka_topic=self.kafka_topic,
                    kafka_group_id=self.kafka_group_id,
                    message_processor=self.message_processor,
                )
                w.start()
                self.workers.append(w)
            print("[Manager] Workers iniciados. Pressione Ctrl+C para parar.")

            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\n[Manager] Interrompido por teclado. Encerrando...")
                self.stop()

        except Exception as e:
            print(f"[Manager] Erro ao iniciar workers: {e}")
            self.stop()

    def stop(self):
        print("[Manager] Parando workers...")
        for w in self.workers:
            try:
                w.stop()
            except Exception as e:
                print(f"[Manager] Erro ao parar worker: {e}")

        try:
            self.database_manager.close()
        except Exception as e:
            print(f"[Manager] Erro ao fechar DatabaseManager: {e}")

        print("[Manager] Todos os workers parados.")


def main():
    KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BROKER_URL", "localhost:29092")
    KAFKA_TOPIC = os.getenv("INPUT_TOPIC", "btg.interpreted")
    KAFKA_GROUP_ID = os.getenv("GROUP_ID", "btg-verify-worker-group")
    WORKER_COUNT = int(os.getenv("WORKER_COUNT", "1"))

    DB_CONFIG = {
        "host": os.getenv("PGHOST", "localhost"),
        "port": int(os.getenv("PGPORT", "5433")),
        "database": os.getenv("PGDATABASE", "postgres"),
        "user": os.getenv("PGUSER", "postgres"),
        "password": os.getenv("PGPASSWORD", "postgres"),
    }

    POST_URL = os.getenv("POST_URL", "https://webhook.pedro-porto.com/api/processar")

    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama")
    LLM_MODEL = os.getenv("LLM_MODEL", "qwen2.5:7b-instruct")
    LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.3"))
    OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "https://ollama.pedro-porto.com")

    print("[Main] Iniciando Kafka Worker Manager...")

    database_manager = DatabaseManager(**DB_CONFIG)
    api_client = APIClient(POST_URL)
    llm = LLMWrapper(
        provider=LLM_PROVIDER,
        model=LLM_MODEL,
        temperature=LLM_TEMPERATURE,
        ollama_base_url=OLLAMA_BASE_URL,
    )

    manager = WorkerManager(
        kafka_bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        kafka_topic=KAFKA_TOPIC,
        kafka_group_id=KAFKA_GROUP_ID,
        database_manager=database_manager,
        api_client=api_client,
        llm=llm,
        worker_count=WORKER_COUNT,
    )

    manager.start()


if __name__ == "__main__":
    main()
