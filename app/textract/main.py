import boto3
from aws_call import process_image
import base64
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core.kafka import KafkaJSON


KAFKA_BROKER = os.getenv("KAFKA_BROKER", "localhost:29092")
KAFKA_GROUP_ID = os.getenv("KAFKA_GROUP_ID", "textract-group-1")
INPUT_TOPIC = os.getenv("INPUT_TOPIC", "btg.raw")
OUTPUT_TOPIC = os.getenv("OUTPUT_TOPIC", "btg.parsed")

AWS_PROFILE = os.getenv("AWS_PROFILE", "default")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")


client = None
kafka = None


def on_msg(topic, data):
    print("Recebido do tópico:", topic, "=>")
    image64 = data.get("attachment_data")
    image_bytes = base64.b64decode(image64)

    results = process_image(client, image_bytes)

    kafka.send(
        OUTPUT_TOPIC,
        {
            "source_id": data.get("source_id"),
            "attachment_parsed": results,
            "timestamp": data.get("timestamp"),
        },
    )
    print("Resultado enviado para", OUTPUT_TOPIC)


def main():
    global client, kafka

    kafka = KafkaJSON(broker=KAFKA_BROKER, group_id=KAFKA_GROUP_ID)

    session = boto3.Session(profile_name=AWS_PROFILE)
    client = session.client("textract", region_name=AWS_REGION)

    kafka.subscribe(INPUT_TOPIC)
    kafka.loop(on_msg)


if __name__ == "__main__":
    main()
