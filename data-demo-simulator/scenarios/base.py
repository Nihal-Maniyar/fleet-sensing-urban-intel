"""Base scenario interfaces and event emitters for multiple transport targets."""

from __future__ import annotations

import abc
import json
import os
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

try:
    from events.schema import Event
    from events.storage import SQLiteOutbox
except (ImportError, ValueError):
    from ..events.schema import Event
    from ..events.storage import SQLiteOutbox


class BaseEmitter(abc.ABC):
    """Abstract event emission target."""

    @abc.abstractmethod
    def emit(self, event: Event) -> bool:
        """Emit a single contract-valid event. Returns True on success."""
        pass

    def close(self) -> None:
        """Clean up any open handles or connections."""
        pass


class StdoutEmitter(BaseEmitter):
    """Outputs events to stdout in JSON or pretty format."""

    def __init__(self, pretty: bool = True, ndjson: bool = False) -> None:
        self.pretty = pretty
        self.ndjson = ndjson

    def emit(self, event: Event) -> bool:
        if self.ndjson:
            sys.stdout.write(event.to_json() + "\n")
        elif self.pretty:
            sys.stdout.write(event.to_json(indent=2) + "\n")
        else:
            sys.stdout.write(
                f"[{event.timestamp}] {event.bus_id} -> {event.event_id}: {event.event_type} "
                f"({event.latitude:.5f}, {event.longitude:.5f}) conf={event.confidence:.2f} "
                f"severity={event.severity} [{event.connectivity_state}]\n"
            )
        sys.stdout.flush()
        return True


class FileEmitter(BaseEmitter):
    """Appends events to a file (NDJSON or JSON list)."""

    def __init__(self, output_path: str, format: str = "ndjson") -> None:
        self.output_path = output_path
        self.format = format.lower()
        self._events: List[Dict[str, Any]] = []
        Path(self.output_path).parent.mkdir(parents=True, exist_ok=True)
        if self.format == "ndjson":
            self._file = open(self.output_path, "a", encoding="utf-8")
        else:
            self._file = None

    def emit(self, event: Event) -> bool:
        if self.format == "ndjson" and self._file:
            self._file.write(event.to_json() + "\n")
            self._file.flush()
        else:
            self._events.append(event.to_dict())
        return True

    def close(self) -> None:
        if self.format == "ndjson" and self._file:
            self._file.close()
        elif self.format == "json":
            with open(self.output_path, "w", encoding="utf-8") as f:
                json.dump(self._events, f, indent=2)


class SQLiteEmitter(BaseEmitter):
    """Stores events into the local edge SQLite WAL outbox queue."""

    def __init__(self, db_path: str = "runtime/edge_outbox.db") -> None:
        self.outbox = SQLiteOutbox(db_path=db_path)

    def emit(self, event: Event) -> bool:
        return self.outbox.enqueue(event)


class HTTPEmitter(BaseEmitter):
    """Emits events via HTTP POST to the backend ingestion endpoint."""

    def __init__(self, endpoint_url: str = "http://localhost:8000/api/v1/events", timeout: float = 5.0) -> None:
        self.endpoint_url = endpoint_url
        self.timeout = timeout

    def emit(self, event: Event) -> bool:
        payload = event.to_json().encode("utf-8")
        req = urllib.request.Request(
            self.endpoint_url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return 200 <= resp.status < 300
        except Exception as exc:
            sys.stderr.write(f"HTTP emission failed to {self.endpoint_url}: {exc}\n")
            return False


class MQTTEmitter(BaseEmitter):
    """Emits events over MQTT to topic 'beyonders/events/v1'."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 1883,
        topic: str = "beyonders/events/v1",
        client_id: str = "simulator-publisher",
    ) -> None:
        self.host = host
        self.port = port
        self.topic = topic
        self.client_id = client_id
        self._client = None
        self._init_client()

    def _init_client(self) -> None:
        try:
            import paho.mqtt.client as mqtt  # type: ignore

            self._client = mqtt.Client(client_id=self.client_id)
            self._client.connect(self.host, self.port, keepalive=60)
            self._client.loop_start()
        except ImportError:
            sys.stderr.write(
                "paho-mqtt is not installed. To enable live MQTT publishing, "
                "run: pip install -r data-demo-simulator/requirements.txt\n"
            )
            self._client = None
        except Exception as exc:
            sys.stderr.write(f"Failed to connect to MQTT broker {self.host}:{self.port}: {exc}\n")
            self._client = None

    def emit(self, event: Event) -> bool:
        if self._client is None:
            return False
        payload = event.to_json()
        info = self._client.publish(self.topic, payload, qos=1)
        info.wait_for_publish(timeout=3.0)
        return info.is_published()

    def close(self) -> None:
        if self._client is not None:
            self._client.loop_stop()
            self._client.disconnect()


class CompositeEmitter(BaseEmitter):
    """Dispatches each event to multiple underlying emitters."""

    def __init__(self, emitters: List[BaseEmitter]) -> None:
        self.emitters = emitters

    def emit(self, event: Event) -> bool:
        results = [emitter.emit(event) for emitter in self.emitters]
        return all(results)

    def close(self) -> None:
        for emitter in self.emitters:
            emitter.close()


class BaseScenario(abc.ABC):
    """Abstract base class for deterministic simulator scenarios."""

    name: str = "base_scenario"
    description: str = ""

    @abc.abstractmethod
    def generate_events(self) -> List[Event]:
        """Generate deterministic sequence of contract-valid events."""
        pass

    def run(self, emitter: BaseEmitter, delay_seconds: float = 0.0) -> List[Event]:
        """Execute the scenario, sending each event to the emitter."""
        events = self.generate_events()
        for i, event in enumerate(events):
            emitter.emit(event)
            if delay_seconds > 0 and i < len(events) - 1:
                time.sleep(delay_seconds)
        emitter.close()
        return events
