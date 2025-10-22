# gphoto2 Camera Server

Flask-Server-Applikation zur Steuerung einer Kamera über gphoto2.

## Features

- **Persistente Kameraverbindung**: Die Verbindung zur Kamera wird konstant gehalten
- **Foto-Aufnahme per GET-Request**: Einfache API zum Auslösen und Herunterladen von Fotos
- **Automatischer Download**: Fotos werden direkt als JPG-Download im Browser bereitgestellt
- **Status-Monitoring**: Endpunkte zur Überprüfung der Kameraverbindung

## Voraussetzungen

- Python 3.8+
- libgphoto2 (System-Bibliothek)
- Eine kompatible Kamera (per USB verbunden)

### libgphoto2 Installation

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get update
sudo apt-get install libgphoto2-dev
```

## Installation

```bash
# Dependencies installieren
pip install -r requirements.txt

# Oder mit Poetry
poetry install
```

## Server starten

```bash
python -m app.camera_server
```

Der Server läuft auf `http://localhost:5000`

## API-Endpunkte

### 1. Status prüfen
```bash
GET http://localhost:5000/status
```

### 2. Foto aufnehmen und herunterladen
```bash
GET http://localhost:5000/capture
```

Im Browser: `http://localhost:5000/capture`

### 3. Kamera-Informationen
```bash
GET http://localhost:5000/info
```

### 4. API-Übersicht
```bash
GET http://localhost:5000/
```

## Beispiele

**Im Browser:**
1. Server starten: `python -m app.camera_server`
2. Browser öffnen: `http://localhost:5000/capture`
3. Das Foto wird automatisch aufgenommen und heruntergeladen

**Mit curl:**
```bash
# Foto aufnehmen und speichern
curl -o mein_foto.jpg http://localhost:5000/capture

# Status prüfen
curl http://localhost:5000/status
```

## Architektur

- **`camera_manager.py`**: Verwaltet die persistente Kameraverbindung
- **`camera_server.py`**: Flask-Applikation mit API-Endpunkten
- **`__init__.py`**: Package-Initialisierung

## Logging

Der Server loggt alle wichtigen Ereignisse in der Konsole:
- Kameraverbindung
- Foto-Aufnahmen
- Fehler
