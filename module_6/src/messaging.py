"""Share broker configuration and durable topology between both services."""

import os

import pika

EXCHANGE = "gradcafe.jobs"
QUEUE = "gradcafe.worker"
ROUTING_KEY = "jobs"


def connect():
    """Open a broker connection using environment settings."""
    parameters = pika.ConnectionParameters(
        host=os.getenv("RABBITMQ_HOST", "localhost"),
        port=int(os.getenv("RABBITMQ_PORT", "5672")),
        credentials=pika.PlainCredentials(
            os.getenv("RABBITMQ_USER", "guest"),
            os.getenv("RABBITMQ_PASSWORD", "guest"),
        ),
        heartbeat=60,
        blocked_connection_timeout=30,
        connection_attempts=3,
        retry_delay=2,
    )
    return pika.BlockingConnection(parameters)


def declare_topology(connection):
    """Declare the same exchange, queue, and binding on both sides."""
    channel = connection.channel()
    channel.exchange_declare(exchange=EXCHANGE, exchange_type="direct", durable=True)
    channel.queue_declare(queue=QUEUE, durable=True)
    channel.queue_bind(queue=QUEUE, exchange=EXCHANGE, routing_key=ROUTING_KEY)
    return channel
