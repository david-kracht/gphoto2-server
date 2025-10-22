# Dependencies installieren
poetry install

# Server starten
poetry run gphoto-server

# Oder direkt
poetry run python -m app.camera_server



# RAW-Format (kameraspezifisch)
http://localhost:5000/capture?format=raw

# JPEG-Format
http://localhost:5000/capture?format=jpeg&f-number=f/8&flashshutterspeed=1s&imagesize=3680x2456&iso=25600&orientation=90

# RAW mit zusätzlichen Einstellungen
http://localhost:5000/capture?format=raw&iso=800&shutterspeed=1/200

# JPEG mit ISO
http://localhost:5000/capture?format=jpeg&iso=400