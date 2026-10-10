"""Check durable delivery, acknowledgement behavior, and service entrypoints."""

import json
import sys
from types import SimpleNamespace
from unittest.mock import Mock

import pika
import psycopg
import pytest

from module_6.src import messaging
from module_6.src.db import load_data
from module_6.src.web import publisher, run as web_run
from module_6.src.web.app import flask_app
from module_6.src.worker import consumer

pytestmark = pytest.mark.integration


@pytest.fixture
def broker(monkeypatch):
    """Replace only the broker connection; exercise real topology declarations."""
    connection = Mock()
    connector = Mock(return_value=connection)
    monkeypatch.setattr(messaging.pika, "BlockingConnection", connector)
    monkeypatch.setenv("RABBITMQ_HOST", "test-broker")
    monkeypatch.setenv("RABBITMQ_PORT", "5673")
    monkeypatch.setenv("RABBITMQ_USER", "test-user")
    monkeypatch.setenv("RABBITMQ_PASSWORD", "test-password")
    return connection, connection.channel.return_value, connector


def test_publisher_uses_durable_topology_and_persistent_confirmed_messages(broker):
    connection, channel, connector = broker
    publisher.publish_job({"task": "noop"})

    parameters = connector.call_args.args[0]
    assert parameters.host == "test-broker"
    assert parameters.port == 5673
    assert parameters.credentials.username == "test-user"
    channel.exchange_declare.assert_called_once_with(
        exchange=messaging.EXCHANGE, exchange_type="direct", durable=True,
    )
    channel.queue_declare.assert_called_once_with(queue=messaging.QUEUE, durable=True)
    channel.queue_bind.assert_called_once_with(
        queue=messaging.QUEUE, exchange=messaging.EXCHANGE, routing_key=messaging.ROUTING_KEY,
    )
    channel.confirm_delivery.assert_called_once()
    published = channel.basic_publish.call_args.kwargs
    assert json.loads(published["body"]) == {"task": "noop"}
    assert published["properties"].delivery_mode == 2
    assert published["properties"].content_type == "application/json"
    assert published["mandatory"] is True
    connection.close.assert_called_once()


def test_publisher_closes_connection_when_publication_fails(broker):
    connection, channel, _ = broker
    channel.basic_publish.side_effect = pika.exceptions.AMQPError()
    with pytest.raises(pika.exceptions.AMQPError):
        publisher.publish_job({"task": "noop"})
    connection.close.assert_called_once()


@pytest.mark.parametrize("job", [None, [], {}, {"task": "unknown"}])
def test_publisher_rejects_unsupported_jobs_before_connecting(job, broker):
    _, _, connector = broker
    with pytest.raises(ValueError):
        publisher.publish_job(job)
    connector.assert_not_called()


def test_worker_acknowledges_only_after_processing(monkeypatch):
    channel = Mock()
    completed = []
    monkeypatch.setattr(consumer, "process_job", lambda job: completed.append(job))
    channel.basic_ack.side_effect = lambda **kwargs: completed.append("ack")
    consumer.handle_message(channel, SimpleNamespace(delivery_tag=7), None, b'{"task":"noop"}')
    assert completed == [{"task": "noop"}, "ack"]
    channel.basic_ack.assert_called_once_with(delivery_tag=7)
    channel.basic_nack.assert_not_called()


@pytest.mark.parametrize("body", [b"invalid-json", b"[]", b'{"task":"unknown"}', b"\xff"])
def test_worker_rejects_bad_jobs_without_requeueing(body):
    channel = Mock()
    consumer.handle_message(channel, SimpleNamespace(delivery_tag=8), None, body)
    channel.basic_ack.assert_not_called()
    channel.basic_nack.assert_called_once_with(delivery_tag=8, requeue=False)


def test_worker_requeues_database_failures(monkeypatch):
    channel = Mock()
    monkeypatch.setattr(consumer, "process_job", Mock(side_effect=psycopg.Error("offline")))
    consumer.handle_message(channel, SimpleNamespace(delivery_tag=9), None, b'{"task":"scrape"}')
    channel.basic_ack.assert_not_called()
    channel.basic_nack.assert_called_once_with(delivery_tag=9, requeue=True)


def test_worker_noop_and_scraper_stand_in(monkeypatch):
    assert consumer.process_job({"task": "noop"}) == {"status": "ok"}
    loader = Mock(return_value={"processed_rows": 0})
    monkeypatch.setattr(consumer, "load_cleaned_records", loader)
    assert consumer.process_job({"task": "scrape"}) == {"processed_rows": 0}
    loader.assert_called_once_with([])


@pytest.mark.parametrize("healthcheck", [False, True])
def test_worker_entrypoint_uses_manual_acks_and_prefetch_one(
    healthcheck, broker, monkeypatch, run_module,
):
    connection, channel, _ = broker
    monkeypatch.setattr(sys, "argv", ["consumer"] + (["--healthcheck"] if healthcheck else []))
    run_module(consumer)
    connection.close.assert_called_once()
    if healthcheck:
        channel.start_consuming.assert_not_called()
    else:
        channel.basic_qos.assert_called_once_with(prefetch_count=1)
        assert channel.basic_consume.call_args.kwargs["auto_ack"] is False
        channel.start_consuming.assert_called_once()


def test_web_entrypoint_initializes_schema_and_binds_port_8080(monkeypatch, run_module):
    loader = Mock()
    app = Mock()
    monkeypatch.setattr(load_data, "load_cleaned_records", loader)
    monkeypatch.setattr(flask_app, "create_app", Mock(return_value=app))
    run_module(web_run)
    loader.assert_called_once_with([])
    app.run.assert_called_once_with(host="0.0.0.0", port=8080)


def test_web_health_and_job_endpoint(client, monkeypatch):
    assert client.get("/health").json == {"status": "ok"}
    publish = Mock()
    monkeypatch.setattr(flask_app, "publish_job", publish)
    response = client.post("/jobs", json={"task": "noop"})
    assert response.status_code == 202
    assert response.json == {"queued": True}
    publish.assert_called_once_with({"task": "noop"})


def test_web_rejects_invalid_jobs(client):
    assert client.post("/jobs", json={"task": "unknown"}).status_code == 400


def test_web_reports_broker_unavailability(client, monkeypatch):
    monkeypatch.setattr(flask_app, "publish_job", Mock(side_effect=pika.exceptions.AMQPError()))
    response = client.post("/jobs", json={"task": "noop"})
    assert response.status_code == 503
    assert response.json == {"error": "Message broker unavailable"}
