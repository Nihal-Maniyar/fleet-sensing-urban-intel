"""Background MQTT Consumer service for Fleet Sensing Urban Intelligence.

Subscribes to 'beyonders/events/v1' according to docs/api-contract.md.
Ingests live sensing events from Actual Bus Simulator or edge gateways,
routes them to the ingestion pipeline, database persistence, and WebSocket broadcast.
"""

from __future__ import annotations

import json
import logging
import os
import threading
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger("urban_intelligence.mqtt_consumer")


class MQTTEventConsumer:
    """Subscribes to MQTT topics and processes incoming edge sensing events."""

    DEFAULT_TOPIC = "beyonders/events/v1"

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        topic: str = DEFAULT_TOPIC,
        client_id: str = "urban-intelligence-backend-consumer",
        on_event_received: Optional[Callable[[Dict[str, Any]], Any]] = None,
    ) -> None:
        self.host = host or os.environ.get("MQTT_HOST", "localhost")
        self.port = port or int(os.environ.get("MQTT_PORT", "1883"))
        self.topic = topic
        self.client_id = client_id
        self.on_event_received = on_event_received
        self.client = None
        self.is_connected = False
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._init_client()

    def _init_client(self) -> None:
        try:
            import paho.mqtt.client as mqtt

            try:
                self.client = mqtt.Client(
                    callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
                    client_id=self.client_id,
                )
            except AttributeError:
                self.client = mqtt.Client(client_id=self.client_id)

            self.client.on_connect = self._on_connect
            self.client.on_disconnect = self._on_disconnect
            self.client.on_message = self._on_message
        except ImportError:
            logger.info("paho-mqtt is not installed; MQTT consumer running in passive mode")
            self.client = None

    def _on_connect(self, client, userdata, flags, rc, *args) -> None:
        if rc == 0:
            self.is_connected = True
            logger.info("MQTT Consumer connected to broker at %s:%d, subscribing to %s", self.host, self.port, self.topic)
            client.subscribe(self.topic)
        else:
            self.is_connected = False
            logger.warning("MQTT Consumer connection returned code %s", rc)

    def _on_disconnect(self, client, userdata, rc, *args) -> None:
        self.is_connected = False
        logger.info("MQTT Consumer disconnected from broker (code: %s)", rc)

    def _on_message(self, client, userdata, message) -> None:
        try:
            payload_str = message.payload.decode("utf-8")
            event_data = json.loads(payload_str)
            logger.info("MQTT received event on %s: %s", message.topic, event_data.get("event_id"))
            if self.on_event_received:
                self.on_event_received(event_data)
        except Exception as e:
            logger.error("Failed to process MQTT message payload: %s", e)

    def start(self) -> bool:
        """Start the MQTT consumer in a background thread."""
        if not self.client:
            return False
        try:
            self.client.connect(self.host, self.port, 60)
            self.client.loop_start()
            self.is_connected = True
            logger.info("MQTT consumer loop started for %s:%d", self.host, self.port)
            return True
        except Exception as e:
            logger.info("MQTT broker not accessible at %s:%d (%s). Will retry or operate in HTTP-only mode.", self.host, self.port, e)
            self.is_connected = False
            return False

    def stop(self) -> None:
        """Stop the background consumer."""
        if self.client:
            try:
                self.client.loop_stop()
                self.client.disconnect()
            except Exception:
                pass
            self.is_connected = False
