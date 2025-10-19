import boto3
from aws_call import process_image
import base64
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.kafka import KafkaJSON


client = None
kafka = None

'''
{
	source_id: int,
	attachment_type: string,
	attachment_data: string,
	timestamp: int
}

'''

def on_msg(topic, data):
    print("Recebido do tópico:", topic, "=>")
    image64 = data.get("attachment_data")
    image_bytes = base64.b64decode(image64)
    results = process_image(client, image_bytes)
    kafka.send('btg.parsed', 
                {
                    "source_id": data.get("source_id"),
                    "attachment_parsed": results,
                    "timestamp": data.get("timestamp")
                })
    print('enviado')




def main():
    global client 
    global kafka
    kafka = KafkaJSON(broker="localhost:29092", group_id="textract-group-1")

    session = boto3.Session(profile_name='default')
    client = session.client('textract', region_name='us-east-1')

    kafka.subscribe('btg.raw')
    kafka.loop(on_msg)
    

if __name__ == "__main__":
    main()
