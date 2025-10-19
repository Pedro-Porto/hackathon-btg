import threading
import os
import sys
from typing import Callable, Optional

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.kafka import KafkaJSON
from message_processor import MessageProcessor


class PartitionWorker:
    """
    Worker baseado no KafkaJSON (consumo simples por tópico).
    Observação: o KafkaJSON não expõe assign direto por partição.
    Se precisar, adicione um filtro no callback (ex.: por chave de roteamento)
    ou estenda o wrapper para aceitar partitions.
    """

    def __init__(
        self,
        partition: int,
        kafka_bootstrap_servers: str,
        kafka_topic: str,
        kafka_group_id: str,
        message_processor: MessageProcessor
    ):
        self.partition = partition
        self.kafka_bootstrap_servers = kafka_bootstrap_servers
        self.kafka_topic = kafka_topic
        self.kafka_group_id = kafka_group_id
        self.message_processor = message_processor

        self._kafka: Optional[KafkaJSON] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False

    def _on_message(self, topic: str, data: dict):
        try:
            print(f"[Worker p{self.partition}] msg de '{topic}': {data}")
            self.message_processor.process(data)
        except Exception as e:
            print(f"[Worker p{self.partition}] erro ao processar: {e}")

    def run(self):
        print(f"[Worker p{self.partition}] iniciando...")
        self._kafka = KafkaJSON(broker=self.kafka_bootstrap_servers, group_id=self.kafka_group_id)
        self._kafka.subscribe(self.kafka_topic)
        self._running = True

        try:
            self._kafka.loop(self._on_message)
        except KeyboardInterrupt:
            print(f"\n[Worker p{self.partition}] interrompido por KeyboardInterrupt")
        finally:
            if self._kafka and hasattr(self._kafka, "close"):
                try:
                    self._kafka.close()
                except Exception:
                    pass
            print(f"[Worker p{self.partition}] parado")

    def start(self):
        if self._thread and self._thread.is_alive():
            print(f"[Worker p{self.partition}] já está rodando")
            return
        self._thread = threading.Thread(
            target=self.run,
            name=f"Worker-Partition-{self.partition}",
            daemon=True,
        )
        self._thread.start()

    def stop(self):
        self._running = False
        if self._kafka and hasattr(self._kafka, "close"):
            try:
                self._kafka.close()
            except Exception:
                pass
        if self._thread:
            self._thread.join(timeout=5)
