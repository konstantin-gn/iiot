"""MQTT-Logger zum Speichern von Sensordaten in CSV und TinyDB."""

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

import paho.mqtt.client as mqtt
from tinydb import TinyDB


def load_config(path: str = "config.json") -> dict:
    """Lädt die MQTT-Konfiguration aus der config.json."""
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def try_parse_number(payload: str):
    """
    Versucht, den empfangenen MQTT-Payload in eine Zahl umzuwandeln.
    Falls das nicht möglich ist, wird None zurückgegeben.
    """
    try:
        value = float(payload)
        return value
    except ValueError:
        return None


def extract_measurement_name(topic: str) -> str:
    """
    Extrahiert den Messnamen aus dem MQTT-Topic.

    """
    parts = topic.split("/")

    if len(parts) >= 4:
        return "/".join(parts[3:])

    return topic


class MqttDataLogger:
    """Empfängt MQTT-Nachrichten und speichert diese in CSV und TinyDB."""

    def __init__(self, config: dict):
        """Initialisiert Logger, CSV, TinyDB und MQTT-Client."""
        self.config = config

        self.group = config["group"]
        self.base_topic = config["base_topic"]

        # Alle Topics der eigenen Gruppe abonnieren
        self.subscribe_topic = f"{self.base_topic}/{self.group}/#"

        self.csv_path = Path(config["csv_path"])
        self.tinydb_path = Path(config["tinydb_path"])

        # Ordner automatisch anlegen, falls sie noch nicht existieren
        self.csv_path.parent.mkdir(parents=True, exist_ok=True)
        self.tinydb_path.parent.mkdir(parents=True, exist_ok=True)

        # TinyDB initialisieren
        self.db = TinyDB(self.tinydb_path)
        self.table = self.db.table("mqtt_messages")

        # CSV-Datei vorbereiten
        self._init_csv()

        # MQTT-Client erstellen
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.client.username_pw_set(
            username=config["username"],
            password=config["password"],
        )

        # Callback-Funktionen registrieren
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect

    def _init_csv(self):
        """Erstellt die CSV-Datei mit Header, falls sie noch nicht existiert."""
        if not self.csv_path.exists():
            with open(self.csv_path, "w", newline="", encoding="utf-8") as file:
                writer = csv.writer(file)
                writer.writerow(
                    [
                        "timestamp",
                        "unix_ms",
                        "topic",
                        "measurement",
                        "payload_raw",
                        "value",
                        "is_numeric",
                        "qos",
                        "retain",
                    ]
                )

    def on_connect(self, client, userdata, flags, reason_code, properties):
        """Wird ausgeführt, sobald die Verbindung zum Broker aufgebaut ist."""
        print(f"Verbunden mit MQTT-Broker. Status: {reason_code}")
        print(f"Subscribe auf Topic: {self.subscribe_topic}")

        # Abonniert alle Daten der eigenen Gruppe
        client.subscribe(self.subscribe_topic)

    def on_disconnect(self, client, userdata, disconnect_flags, reason_code, properties):
        """Wird ausgeführt, wenn die Verbindung zum Broker getrennt wird."""
        print(f"Verbindung getrennt. Status: {reason_code}")

    def on_message(self, client, userdata, msg):
        """Wird bei jeder empfangenen MQTT-Nachricht ausgeführt."""

        # Zeitstempel der empfangenen Nachricht erzeugen
        timestamp = datetime.now(timezone.utc)
        timestamp_iso = timestamp.isoformat()
        unix_ms = int(timestamp.timestamp() * 1000)

        # MQTT-Inhalte auslesen
        topic = msg.topic
        payload_raw = msg.payload.decode("utf-8", errors="replace")

        # Payload numerisch interpretieren, falls möglich
        value = try_parse_number(payload_raw)
        is_numeric = value is not None

        # Messgröße aus dem Topic ableiten
        measurement = extract_measurement_name(topic)

        # Datensatz für CSV und TinyDB
        record = {
            "timestamp": timestamp_iso,
            "unix_ms": unix_ms,
            "topic": topic,
            "measurement": measurement,
            "payload_raw": payload_raw,
            "value": value,
            "is_numeric": is_numeric,
            "qos": msg.qos,
            "retain": msg.retain,
        }

        # In TinyDB speichern
        self.table.insert(record)

        # In CSV speichern
        with open(self.csv_path, "a", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(
                [
                    record["timestamp"],
                    record["unix_ms"],
                    record["topic"],
                    record["measurement"],
                    record["payload_raw"],
                    record["value"],
                    record["is_numeric"],
                    record["qos"],
                    record["retain"],
                ]
            )

        print(f"{timestamp_iso} | {topic} | {payload_raw}")

    def run(self):
        """Startet den MQTT-Logger dauerhaft."""
        print("Starte MQTT Logger...")
        print(f"Broker: {self.config['broker']}:{self.config['port']}")
        print(f"Gruppe: {self.group}")

        # Verbindung zum Broker aufbauen
        self.client.connect(
            self.config["broker"],
            self.config["port"],
            keepalive=60,
        )

        # Endlosschleife für den MQTT-Empfang
        self.client.loop_forever()


if __name__ == "__main__":
    config = load_config()
    logger = MqttDataLogger(config)
    logger.run()