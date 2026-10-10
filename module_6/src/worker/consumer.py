"""Consume scaffold jobs with manual acknowledgements and prefetch one."""

import json
import logging
import sys

import psycopg

from .. import messaging
from ..db.load_data import load_cleaned_records
from .etl.incremental_scraper import scrape_incrementally

LOGGER = logging.getLogger(__name__)


def process_job(job):
    """Execute the minimal baseline jobs; incremental scraping is a stand-in."""
    if not isinstance(job, dict):
        raise ValueError("A job must be a JSON object")
    if job.get("task") == "noop":
        return {"status": "ok"}
    if job.get("task") == "scrape":
        return load_cleaned_records(scrape_incrementally())
    raise ValueError("Unknown task")


def handle_message(channel, method, _properties, body):
    """Acknowledge successful work and distinguish malformed jobs from failures."""
    try:
        result = process_job(json.loads(body))
    except (ValueError, TypeError):
        LOGGER.warning("Rejected malformed or unsupported job")
        channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
    except (psycopg.Error, RuntimeError):
        LOGGER.exception("Job failed; returning it to the queue")
        channel.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
    else:
        LOGGER.info("Job completed: %s", result)
        channel.basic_ack(delivery_tag=method.delivery_tag)


def main(*, healthcheck=False):
    """Consume jobs, or check broker connectivity for Docker's health check."""
    connection = messaging.connect()
    try:
        if healthcheck:
            return
        channel = messaging.declare_topology(connection)
        channel.basic_qos(prefetch_count=1)
        channel.basic_consume(
            queue=messaging.QUEUE, on_message_callback=handle_message, auto_ack=False,
        )
        channel.start_consuming()
    finally:
        connection.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main(healthcheck="--healthcheck" in sys.argv)
