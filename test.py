from confluent_kafka import Producer
import json
import socket

TOPIC = "commented-email"

# Emails to send
emails = [
    "example.com",

]

def create_producer():
    return Producer({
        "bootstrap.servers": "localhost:9092",
        "client.id": socket.gethostname(),
    })

def produce_emails(producer, topic, emails):
    print(f"🚀 Sending {len(emails)} emails individually to topic '{topic}'...")

    for email in emails:
        payload = {
            "email": email    # <-- YOUR CONSUMER REQUIRES THIS KEY
        }

        json_string = json.dumps(payload)

        producer.produce(topic, json_string.encode("utf-8"))
        print(f"📤 Sent email: {email}")

    producer.flush()
    print("🎉 All emails sent successfully.")

if __name__ == "__main__":
    producer = create_producer()
    produce_emails(producer, TOPIC, emails)
