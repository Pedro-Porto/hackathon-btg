from confluent_kafka import Producer, Consumer
import json

class KafkaJSON:
    """
    Uso:
        k = KafkaJSON(broker="localhost:9092", group_id="meu-grupo")
        k.subscribe("meu-topico")
        k.send("meu-topico", {"hello": "world"})
        k.loop(lambda topic, data: print(topic, data))  # Ctrl+C para parar
    """
    def __init__(self, broker: str = "localhost:9092", group_id: str = "python-client"):
        self._producer = Producer({"bootstrap.servers": broker})
        self._consumer = Consumer({
            "bootstrap.servers": broker,
            "group.id": group_id,
            "auto.offset.reset": "earliest"
        })

    # --- PRODUCER ---
    def send(self, topic: str, data: dict, key: str | None = None) -> None:
        payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self._producer.produce(topic, value=payload, key=key)
        self._producer.flush()

    # --- CONSUMER ---
    def subscribe(self, topics: str | list[str]) -> None:
        if isinstance(topics, str):
            topics = [topics]
        self._consumer.subscribe(topics)

    def poll_once(self, callback, timeout: float = 1.0) -> bool:
        """Faz um poll e chama callback(topic, data_json). Retorna True se processou algo."""
        msg = self._consumer.poll(timeout)
        if msg is None:
            return False
        if msg.error():
            print("Erro:", msg.error())
            return False
        try:
            data = json.loads(msg.value().decode("utf-8"))
        except Exception:
            data = msg.value().decode("utf-8")
        callback(msg.topic(), data)
        return True

    def loop(self, callback, timeout: float = 1.0) -> None:
        try:
            while True:
                self.poll_once(callback, timeout)
        except KeyboardInterrupt:
            pass
        finally:
            self.close()

    # --- FECHAMENTO ---
    def close(self) -> None:
        try:
            self._consumer.close()
        finally:
            self._producer.flush()


if __name__ == "__main__":
    def on_msg(topic, data):
        print("[MSG]", topic, data)

    k = KafkaJSON("localhost:29092", "demo-group")
    k.subscribe("raw.posts")
    k.send("raw.posts", {"ola": "mundo"})
    k.loop(on_msg)
