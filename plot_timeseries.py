"""Plottet eine gespeicherte MQTT-Zeitreihe aus TinyDB."""

import json
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from tinydb import Query, TinyDB


def load_config(path: str = "config.json") -> dict:
    """Lädt die Konfiguration aus der config.json."""
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def main():
    """Lädt Messwerte aus TinyDB und erstellt einen Zeitreihenplot."""

    config = load_config()

    db_path = Path(config["tinydb_path"])
    group = config["group"]
    base_topic = config["base_topic"]

    # Hier wird festgelegt, welche Messgröße geplottet werden soll.
    measurement_name = "rPcntFillLevel"  # Ändern nach Bedarf

    # Vollständiges MQTT-Topic der gewünschten Messgröße
    topic = f"{base_topic}/{group}/{measurement_name}"

    # TinyDB öffnen
    db = TinyDB(db_path)
    table = db.table("mqtt_messages")
    Message = Query()

    # Nur passende numerische Messwerte aus der TinyDB laden
    records = table.search(
        (Message.topic == topic)
        & (Message.is_numeric == True)
    )

    if not records:
        print(f"Keine numerischen Daten für Topic gefunden: {topic}")
        return

    # Datensätze in einen DataFrame umwandeln
    df = pd.DataFrame(records)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp")

    # Zeitreihe plotten
    plt.figure()
    plt.plot(df["timestamp"], df["value"], marker="o")
    plt.xlabel("Zeit")
    plt.ylabel(measurement_name)
    plt.title(f"Zeitreihe: {measurement_name}")
    plt.grid(True)
    plt.xticks(rotation=45)
    plt.tight_layout()

    # Plot speichern
    output_path = Path("data") / f"plot_{measurement_name}.png"
    plt.savefig(output_path, dpi=150)
    plt.show()

    print(f"Plot gespeichert unter: {output_path}")


if __name__ == "__main__":
    main()