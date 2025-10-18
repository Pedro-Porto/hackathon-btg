from kafka import KafkaJSON


kafka = KafkaJSON(broker="localhost:29092", group_id="group-1")




kafka.send("meu-topico", {"evento": "teste", "valor": 123})

def on_msg(topic, data):
    print("Recebido do tópico:", topic, "=>", data)

kafka.subscribe("meu-topico")
kafka.loop(on_msg)  # Ctrl+C para parar
