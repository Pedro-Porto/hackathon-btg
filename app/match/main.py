import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.kafka import KafkaJSON
from message_matcher import MessageMatcher
from database_matcher import DatabaseMatcher
from core.llm import LLMWrapper


class MatchWorker:
    
    def __init__(
        self,
        kafka_broker: str,
        input_topic: str,
        group_id: str,
        database_matcher: DatabaseMatcher,
        llm: LLMWrapper
    ):
        self.kafka_client = KafkaJSON(broker=kafka_broker, group_id=group_id)
        self.input_topic = input_topic
        self.database_matcher = database_matcher
        self.message_matcher = MessageMatcher(database_matcher, self.kafka_client, llm)
    
    def process_message(self, topic: str, data: dict):
        print(f"Message received from topic '{topic}'")
        self.message_matcher.process(data)
    
    def start(self):
        print(f"Starting Match Worker...")
        print(f"Subscribing to topic: {self.input_topic}")
        print("Press Ctrl+C to stop\n")
        
        self.kafka_client.subscribe(self.input_topic)
        
        try:
            self.kafka_client.loop(self.process_message)
        finally:
            self.database_matcher.close()
            print("Worker stopped")


def main():
    KAFKA_BROKER = os.getenv("KAFKA_BROKER_URL", "localhost:29092")
    INPUT_TOPIC = os.getenv("INPUT_TOPIC", "btg.enriched")
    GROUP_ID = os.getenv("GROUP_ID", "btg-match-worker-group")

    DB_CONFIG = {
        'host': os.getenv('PGHOST', 'localhost'),
        'port': int(os.getenv('PGPORT', '5433')),
        'database': os.getenv('PGDATABASE', 'postgres'),
        'user': os.getenv('PGUSER', 'postgres'),
        'password': os.getenv('PGPASSWORD', 'postgres'),
    }

    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama")
    LLM_MODEL = os.getenv("LLM_MODEL", "qwen2.5:7b-instruct")
    LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.3"))
    OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "https://ollama.pedro-porto.com")
    
    print("Initializing Match Worker...")
    
    database_matcher = DatabaseMatcher(**DB_CONFIG)
    llm = LLMWrapper(
        provider=LLM_PROVIDER,
        model=LLM_MODEL,
        temperature=LLM_TEMPERATURE,
        ollama_base_url=OLLAMA_BASE_URL
    )
    
    worker = MatchWorker(
        kafka_broker=KAFKA_BROKER,
        input_topic=INPUT_TOPIC,
        group_id=GROUP_ID,
        database_matcher=database_matcher,
        llm=llm
    )
    
    worker.start()


if __name__ == '__main__':
    main()

