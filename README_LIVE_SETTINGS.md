# Live Preview Settings ändern

Sie können jetzt Kamera-Einstellungen während des Live-Preview-Streams ändern, ohne den Stream zu unterbrechen!

## Neuer Endpunkt: `/preview/settings`

### POST Request
Sendet JSON mit den zu ändernden Einstellungen.

```bash
curl -X POST http://localhost:5000/preview/settings \
  -H "Content-Type: application/json" \
  -d '{"iso": "800"}'
```

## Beispiele

### ISO ändern
```bash
curl -X POST http://localhost:5000/preview/settings \
  -H "Content-Type: application/json" \
  -d '{"iso": "1600"}'
```

### Mehrere Einstellungen gleichzeitig
```bash
curl -X POST http://localhost:5000/preview/settings \
  -H "Content-Type: application/json" \
  -d '{"iso": "800", "shutterspeed": "1/200", "whitebalance": "Fluorescent"}'
```

### Mit Python
```python
import requests

# Während der Preview-Stream läuft
response = requests.post(
    'http://localhost:5000/preview/settings',
    json={
        'iso': '1600',
        'shutterspeed': '1/125'
    }
)

result = response.json()
print(f"Erfolg: {result['success']}")
print(f"Angewendet: {result['applied']}/{result['total']}")
print(f"Aktive Streams: {result['active_streams']}")
```

### Mit JavaScript (im Browser während Preview läuft)
```javascript
// ISO ändern
fetch('/preview/settings', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json'
    },
    body: JSON.stringify({
        iso: '800'
    })
})
.then(response => response.json())
.then(data => {
    console.log('Einstellungen geändert:', data);
    if (data.success) {
        alert('ISO erfolgreich geändert!');
    }
});
```

## Response Format

```json
{
    "success": true,
    "applied": 2,
    "total": 2,
    "results": {
        "iso": true,
        "shutterspeed": true
    },
    "active_streams": 1
}
```

## Vorteile

✅ **Kein Stream-Unterbruch**: Preview läuft weiter während Einstellungen geändert werden
✅ **Sofortige Wirkung**: Änderungen sind im nächsten Frame sichtbar
✅ **Mehrere Einstellungen**: Können mehrere Settings gleichzeitig ändern
✅ **Multi-Client sicher**: Funktioniert auch wenn mehrere Browser-Tabs Preview anzeigen

## Welche Einstellungen können geändert werden?

Alle Einstellungen die auch `/settings` anzeigt:
- `iso` - ISO-Wert
- `shutterspeed` - Verschlusszeit
- `aperture` - Blende (f-number)
- `whitebalance` - Weißabgleich
- `focusmode` - Fokus-Modus
- `imageformat` - Bildformat
- und viele mehr...

Welche Einstellungen verfügbar sind, hängt von Ihrer Kamera ab:
```bash
curl http://localhost:5000/settings
```

## Workflow-Beispiel

1. **Preview starten** im Browser: `http://localhost:5000/preview-page`
2. **Einstellungen anzeigen**: `curl http://localhost:5000/settings`
3. **ISO live ändern**: 
   ```bash
   curl -X POST http://localhost:5000/preview/settings \
     -H "Content-Type: application/json" \
     -d '{"iso": "1600"}'
   ```
4. **Ergebnis sofort im Preview sehen** ✨

## Hinweise

- Settings werden mit dem gleichen Lock wie Preview geschützt (Thread-safe)
- Bei ungültigen Werten wird `false` für diese Einstellung zurückgegeben
- Stream läuft unterbrechungsfrei weiter
- Funktioniert auch bei mehreren gleichzeitigen Preview-Streams

## Fortgeschrittenes Beispiel: ISO-Slider

HTML-Seite mit Live-ISO-Steuerung während des Previews:

```html
<!DOCTYPE html>
<html>
<head>
    <title>Live Preview mit Controls</title>
</head>
<body>
    <h1>Camera Preview mit Live-Controls</h1>
    
    <img src="/preview" style="width: 100%; max-width: 800px;">
    
    <div>
        <label>ISO: <span id="iso-value">800</span></label><br>
        <input type="range" id="iso-slider" 
               min="100" max="6400" step="100" value="800"
               oninput="changeISO(this.value)">
    </div>
    
    <script>
        function changeISO(value) {
            document.getElementById('iso-value').textContent = value;
            
            fetch('/preview/settings', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({iso: value})
            })
            .then(r => r.json())
            .then(data => {
                if (!data.success) {
                    console.error('ISO change failed:', data);
                }
            });
        }
    </script>
</body>
</html>
```

Das Preview-Bild ändert sich live während Sie den Slider bewegen! 🎚️
