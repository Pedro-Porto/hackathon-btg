import os
import sys
import time
import json
import base64
from typing import Optional

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.kafka import KafkaJSON


class RawPublisher:
    """
    Publicador simples para o tópico btg.raw (ou outro), usando seu KafkaJSON.
    - Conecta no __init__ (ou via with ... as ...)
    - publish() envia payload já montado
    - publish_base64() envia string base64 como attachment_data
    - publish_file() lê um arquivo binário e envia em base64 com padding correto
    """

    def __init__(
        self,
        broker_url: Optional[str] = None,
        topic: Optional[str] = None,
        *,
        auto_connect: bool = True,
    ):
        self.broker_url = broker_url or os.getenv("KAFKA_BROKER_URL", "localhost:29092")
        self.topic = topic or os.getenv("TOPIC_OUT_NAME", "btg.raw")
        self._kafka: Optional[KafkaJSON] = None

        if auto_connect:
            self.connect()

    # --------- ciclo de vida ----------
    def connect(self) -> None:
        """Estabelece a conexão com o Kafka usando KafkaJSON."""
        print(f"Tentando conectar ao broker Kafka em {self.broker_url}...")
        try:
            self._kafka = KafkaJSON(broker=self.broker_url)
            print("Conexão com o Kafka estabelecida com sucesso!")
        except Exception as e:
            self._kafka = None
            raise RuntimeError(f"Não foi possível conectar ao Kafka: {e}") from e

    def close(self) -> None:
        """Fecha o cliente, se o seu KafkaJSON expuser algo para fechar."""
        # Se seu KafkaJSON tiver .close(), chame aqui. Se não, ignore.
        if hasattr(self._kafka, "close") and callable(getattr(self._kafka, "close")):
            try:
                self._kafka.close()  # type: ignore[attr-defined]
            except Exception:
                pass

    # permite usar: with RawPublisher(...) as pub: ...
    def __enter__(self):
        if self._kafka is None:
            self.connect()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()

    # --------- helpers ----------
    @staticmethod
    def _now_ms() -> int:
        return int(time.time() * 1000)

    def _ensure_client(self) -> KafkaJSON:
        if self._kafka is None:
            raise RuntimeError("Kafka não conectado. Chame connect() primeiro.")
        return self._kafka

    # --------- APIs de publicação ----------
    def publish(
        self,
        *,
        source_id: int,
        attachment_type: str,
        attachment_data: str,
        timestamp_ms: Optional[int] = None,
    ) -> None:
        """
        Publica uma mensagem já com attachment_data pronto (ex.: base64).
        """
        payload = {
            "source_id": int(source_id),
            "attachment_type": str(attachment_type),
            "attachment_data": str(attachment_data),
            "timestamp": int(timestamp_ms if timestamp_ms is not None else self._now_ms()),
        }

        print(f"Publicando no tópico '{self.topic}': {json.dumps(payload)[:400]}...")
        try:
            k = self._ensure_client()
            # Usa send() se existir, senão publish()
            if hasattr(k, "send") and callable(getattr(k, "send")):
                k.send(self.topic, payload)  # type: ignore[attr-defined]
            elif hasattr(k, "publish") and callable(getattr(k, "publish")):
                k.publish(self.topic, payload)  # type: ignore[attr-defined]
            else:
                raise AttributeError("KafkaJSON não possui 'send' nem 'publish'.")
            print("Mensagem publicada com sucesso!")
        except Exception as e:
            print(f"Erro ao publicar: {e}")
            raise

    def publish_base64(
        self,
        *,
        source_id: int,
        attachment_type: str,
        b64_data: str,
        timestamp_ms: Optional[int] = None,
    ) -> None:
        """Envia uma string base64 (já pronta) como attachment_data."""
        # opcional: uma validação rápida de padding (não decodifica)
        if len(b64_data) % 4 == 1:
            raise ValueError("Base64 inválido (comprimento ≡ 1 mod 4).")
        self.publish(
            source_id=source_id,
            attachment_type=attachment_type,
            attachment_data=b64_data,
            timestamp_ms=timestamp_ms,
        )

    def publish_file(
        self,
        *,
        source_id: int,
        filepath: str,
        attachment_type: str = "image",
        timestamp_ms: Optional[int] = None,
    ) -> None:
        """
        Lê um arquivo binário e envia como base64 (padding correto, sem quebras).
        Ideal para imagens: attachment_type="image".
        """
        if not os.path.isfile(filepath):
            raise FileNotFoundError(f"Arquivo não encontrado: {filepath}")
        with open(filepath, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("ascii")
        self.publish(
            source_id=source_id,
            attachment_type=attachment_type,
            attachment_data=b64,
            timestamp_ms=timestamp_ms,
        )
