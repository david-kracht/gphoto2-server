# Flexible Config & Preview Settings API

Beide Endpunkte `/config` und `/preview/settings` unterstützen jetzt eine flexible Read/Write Logik mit GET und POST.

## Logik

**Automatische Erkennung:**
- **KEINE Parameter** → **READ** (aktuelle Werte zurückgeben)
- **MIT Parametern** → **WRITE** (Werte setzen)

Dies funktioniert sowohl für GET (URL-Parameter) als auch POST (JSON-Body).

## `/config` - Kamera-Konfiguration

### READ: Aktuelle Settings abrufen

```bash
# GET ohne Parameter
curl http://localhost:5000/config

# POST ohne Body
curl -X POST http://localhost:5000/config
```

**Response:**
```json
{
  "mode": "read",
  "count": 42,
  "settings": {
    "iso": {
      "current": "800",
      "type": "radio",
      "choices": ["100", "200", "400", "800", "1600", "3200"]
    },
    "shutterspeed": {
      "current": "1/200",
      "type": "radio",
      "choices": ["1/4000", "1/2000", "1/1000", "1/500", "1/200"]
    }
  }
}
```

### WRITE: Settings setzen

#### Via GET (URL-Parameter)
```bash
# Einzelner Wert
curl "http://localhost:5000/config?iso=1600"

# Mehrere Werte
curl "http://localhost:5000/config?iso=800&shutterspeed=1/200&whitebalance=Fluorescent"
```

#### Via POST (JSON)
```bash
# Einzelner Wert
curl -X POST http://localhost:5000/config \
  -H "Content-Type: application/json" \
  -d '{"iso": "1600"}'

# Mehrere Werte
curl -X POST http://localhost:5000/config \
  -H "Content-Type: application/json" \
  -d '{"iso": "800", "shutterspeed": "1/200"}'
```

**Response:**
```json
{
  "mode": "write",
  "success": true,
  "applied": 2,
  "total": 2,
  "results": {
    "iso": true,
    "shutterspeed": true
  }
}
```

## `/preview/settings` - Live Preview Settings

Gleiche Logik wie `/config`, aber funktioniert während der Preview läuft.

### READ: Aktuelle Settings während Preview

```bash
# GET ohne Parameter
curl http://localhost:5000/preview/settings

# POST ohne Body
curl -X POST http://localhost:5000/preview/settings
```

**Response:**
```json
{
  "mode": "read",
  "active_streams": 2,
  "settings": {
    "iso": {"current": "800", "type": "radio", "choices": [...]},
    "shutterspeed": {"current": "1/200", "type": "radio", "choices": [...]}
  }
}
```

### WRITE: Settings während Preview ändern

#### Via GET (URL-Parameter)
```bash
# Einzeln - Einfach im Browser eingeben!
http://localhost:5000/preview/settings?iso=1600

# Mehrere
curl "http://localhost:5000/preview/settings?iso=800&shutterspeed=1/125"
```

#### Via POST (JSON)
```bash
curl -X POST http://localhost:5000/preview/settings \
  -H "Content-Type: application/json" \
  -d '{"iso": "800"}'
```

**Response:**
```json
{
  "mode": "write",
  "success": true,
  "applied": 1,
  "total": 1,
  "results": {"iso": true},
  "active_streams": 2
}
```

## Vorteile der GET-Methode

### 1. **Browser-freundlich**
Einfach URL im Browser eingeben:
```
http://localhost:5000/config?iso=1600
```

### 2. **Einfache Bookmarks**
Speichern Sie häufig verwendete Einstellungen als Lesezeichen:
- `http://localhost:5000/config?iso=800&shutterspeed=1/200` → "Studio Setup"
- `http://localhost:5000/config?iso=3200&shutterspeed=1/60` → "Low Light"

### 3. **HTML-Links**
```html
<a href="/preview/settings?iso=100">ISO 100</a>
<a href="/preview/settings?iso=400">ISO 400</a>
<a href="/preview/settings?iso=1600">ISO 1600</a>
```

### 4. **Einfache Scripts**
```bash
#!/bin/bash
# Schnelle Preset-Wechsel
curl "http://localhost:5000/config?iso=800&shutterspeed=1/200"
```

## Beispiel: HTML Control Panel

```html
<!DOCTYPE html>
<html>
<head>
    <title>Camera Control Panel</title>
</head>
<body>
    <h1>Live Preview mit Controls</h1>
    
    <!-- Preview Stream -->
    <img src="/preview" style="width: 100%; max-width: 800px;">
    
    <!-- Quick ISO Buttons (GET-Requests) -->
    <h2>ISO Quick-Select</h2>
    <a href="/preview/settings?iso=100">
        <button>ISO 100</button>
    </a>
    <a href="/preview/settings?iso=400">
        <button>ISO 400</button>
    </a>
    <a href="/preview/settings?iso=800">
        <button>ISO 800</button>
    </a>
    <a href="/preview/settings?iso=1600">
        <button>ISO 1600</button>
    </a>
    <a href="/preview/settings?iso=3200">
        <button>ISO 3200</button>
    </a>
    
    <!-- Preset Buttons -->
    <h2>Presets</h2>
    <a href="/preview/settings?iso=100&shutterspeed=1/200&whitebalance=Daylight">
        <button>☀️ Daylight</button>
    </a>
    <a href="/preview/settings?iso=800&shutterspeed=1/60&whitebalance=Fluorescent">
        <button>💡 Indoor</button>
    </a>
    <a href="/preview/settings?iso=3200&shutterspeed=1/30&whitebalance=Tungsten">
        <button>🌙 Low Light</button>
    </a>
    
    <!-- Current Settings Display -->
    <h2>Current Settings</h2>
    <div id="current-settings">Loading...</div>
    
    <script>
        // Load and display current settings
        function loadSettings() {
            fetch('/preview/settings')
                .then(r => r.json())
                .then(data => {
                    if (data.mode === 'read') {
                        let html = '<ul>';
                        for (let [key, val] of Object.entries(data.settings)) {
                            html += `<li><strong>${key}:</strong> ${val.current}</li>`;
                        }
                        html += '</ul>';
                        document.getElementById('current-settings').innerHTML = html;
                    }
                });
        }
        
        // Initial load
        loadSettings();
        
        // Refresh every 5 seconds
        setInterval(loadSettings, 5000);
    </script>
</body>
</html>
```

## Python-Beispiele

### Settings lesen
```python
import requests

# Aktuelle Settings abrufen
response = requests.get('http://localhost:5000/config')
data = response.json()

if data['mode'] == 'read':
    print(f"Found {data['count']} settings")
    iso = data['settings']['iso']['current']
    print(f"Current ISO: {iso}")
```

### Settings setzen (GET)
```python
# Via URL-Parameter (einfachste Methode)
response = requests.get(
    'http://localhost:5000/config',
    params={'iso': '800', 'shutterspeed': '1/200'}
)

result = response.json()
print(f"Mode: {result['mode']}")  # 'write'
print(f"Success: {result['success']}")
```

### Settings setzen (POST)
```python
# Via JSON (traditionelle Methode)
response = requests.post(
    'http://localhost:5000/config',
    json={'iso': '800', 'shutterspeed': '1/200'}
)

result = response.json()
print(f"Applied: {result['applied']}/{result['total']}")
```

## Zusammenfassung

| Endpunkt | Methode | Parameter | Aktion |
|----------|---------|-----------|--------|
| `/config` | GET | Keine | READ: Settings abrufen |
| `/config` | GET | `?iso=800` | WRITE: ISO setzen |
| `/config` | POST | Kein Body | READ: Settings abrufen |
| `/config` | POST | `{"iso":"800"}` | WRITE: ISO setzen |
| `/preview/settings` | GET | Keine | READ während Preview |
| `/preview/settings` | GET | `?iso=800` | WRITE während Preview |
| `/preview/settings` | POST | Kein Body | READ während Preview |
| `/preview/settings` | POST | `{"iso":"800"}` | WRITE während Preview |

**Vorteile:**
✅ Flexible API - ein Endpunkt für Read & Write
✅ Browser-freundlich - URL-Parameter funktionieren direkt
✅ Bookmarks möglich für häufige Einstellungen
✅ Einfache HTML-Integration mit Links/Buttons
✅ Abwärtskompatibel mit bisherigem POST/JSON Code
