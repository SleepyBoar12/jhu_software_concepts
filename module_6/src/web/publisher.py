"""Publish persistent jobs to the worker's durable RabbitMQ queue."""

import json

import pika

from .. import messaging


def publish_job(job):
    """Confirm publication of a supported scaffold job."""
    if not isinstance(job, dict) or job.get("task") not in ("noop", "scrape"):
        raise ValueError("task must be 'noop' or 'scrape'")
    body = json.dumps(job).encode("utf-8")
    connection = messaging.connect()
    try:
        channel = messaging.declare_topology(connection)
        channel.confirm_delivery()
        channel.basic_publish(
            exchange=messaging.EXCHANGE,
            routing_key=messaging.ROUTING_KEY,
            body=body,
            properties=pika.BasicProperties(delivery_mode=2, content_type="application/json"),
            mandatory=True,
        )
    finally:
        connection.close()
