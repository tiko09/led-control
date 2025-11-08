# LED Control Service Installation

Dieses Verzeichnis enthält Dateien zur Installation von LED Control als systemd Service.

## Automatische Installation

```bash
sudo ./install-service.sh
```

Das Script:
- Erstellt automatisch die Service-Datei mit korrekten Pfaden
- Aktiviert den Service für Autostart beim Booten
- Bietet an, den Service sofort zu starten

## Manuelle Installation

Falls Sie die Service-Datei manuell anpassen möchten:

1. **Service-Datei kopieren:**
   ```bash
   sudo cp ledcontrol.service /etc/systemd/system/
   ```

2. **Service-Datei anpassen (optional):**
   ```bash
   sudo nano /etc/systemd/system/ledcontrol.service
   ```
   
   Wichtige Parameter:
   - `WorkingDirectory`: Pfad zum led-control Verzeichnis
   - `ExecStart`: Kommando mit LED-Parametern (z.B. --led_count, --led_pixel_order)

3. **Service aktivieren:**
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable ledcontrol
   sudo systemctl start ledcontrol
   ```

## Service-Verwaltung

### Status prüfen
```bash
sudo systemctl status ledcontrol
```

### Service starten/stoppen
```bash
sudo systemctl start ledcontrol
sudo systemctl stop ledcontrol
sudo systemctl restart ledcontrol
```

### Logs anzeigen
```bash
# Live-Logs (Echtzeit)
sudo journalctl -u ledcontrol -f

# Letzte 100 Zeilen
sudo journalctl -u ledcontrol -n 100

# Logs seit heute
sudo journalctl -u ledcontrol --since today
```

### Autostart deaktivieren/aktivieren
```bash
sudo systemctl disable ledcontrol  # Deaktiviert Autostart
sudo systemctl enable ledcontrol   # Aktiviert Autostart
```

## LED-Konfiguration ändern

Um Parameter wie LED-Anzahl oder Pixel-Order zu ändern:

1. Service stoppen:
   ```bash
   sudo systemctl stop ledcontrol
   ```

2. Service-Datei bearbeiten:
   ```bash
   sudo nano /etc/systemd/system/ledcontrol.service
   ```
   
   Zeile ändern:
   ```
   ExecStart=/usr/local/bin/ledcontrol --led_count 144 --led_pixel_order GRBW
   ```

3. Service neu laden und starten:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl start ledcontrol
   ```

## Troubleshooting

### Service startet nicht

1. **Logs prüfen:**
   ```bash
   sudo journalctl -u ledcontrol -n 50
   ```

2. **Manuell testen:**
   ```bash
   sudo ledcontrol --led_count 144 --led_pixel_order GRBW
   ```

3. **Berechtigungen prüfen:**
   - Service läuft als `root` (benötigt für GPIO/SPI Zugriff)
   - Python-Packages installiert: `pip list | grep rpi`

### Service läuft, aber LEDs zeigen nichts

1. **Einstellungen prüfen:**
   - Webinterface: http://raspberrypi.local
   - Config-Datei: `/etc/ledcontrol.json`

2. **Hardware prüfen:**
   - LED-Streifen richtig angeschlossen?
   - Stromversorgung ausreichend?
   - Richtiger GPIO-Pin? (Standard: GPIO 10 für SPI)

### Performance-Probleme

Bei zu wenig Performance (ruckelnde Animationen):
```bash
# Service-Priorität erhöhen
sudo systemctl edit ledcontrol
```

Hinzufügen:
```ini
[Service]
Nice=-10
IOSchedulingClass=realtime
IOSchedulingPriority=0
```

## Deinstallation

```bash
sudo systemctl stop ledcontrol
sudo systemctl disable ledcontrol
sudo rm /etc/systemd/system/ledcontrol.service
sudo systemctl daemon-reload
```
