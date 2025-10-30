# Multi-Raspberry Pi Discovery & Control

This feature allows multiple Raspberry Pi LED controllers running on the same network to discover each other and synchronize their settings.

## Features

### Backend (Python)
- **mDNS/Zeroconf Discovery**: Automatic discovery of other Pis using `_ledcontrol._tcp.local.` service
- **Pi Identity**: Each Pi broadcasts its device name, group, and version
- **Health Monitoring**: Tracks online/offline status of discovered Pis
- **REST API**: Pi-to-Pi communication for syncing settings
- **Master Mode**: Optional auto-sync to all Pis in the same group

### Frontend (Vue.js)
- **Discovery Page**: Visual display of all discovered Pis
- **Real-time Updates**: WebSocket-based status updates
- **Sync Controls**: 
  - Sync to individual Pi
  - Sync to all Pis in a group
  - Jump to another Pi's web interface
- **Group Filtering**: Filter display by group name
- **Status Indicators**: Online/offline status with last-seen timestamp

## API Endpoints

### GET /api/pi/info
Returns information about this Pi:
```json
{
  "device_name": "Living Room LEDs",
  "hostname": "raspberrypi",
  "group": "living-room",
  "master_mode": false,
  "version": "2.0.0",
  "led_count": 300
}
```

### GET /api/pi/state
Returns current animation state:
```json
{
  "device_name": "Living Room LEDs",
  "group": "living-room",
  "settings": {
    "global_brightness": 1.0,
    "global_color_temp": 6500,
    "global_saturation": 1.0,
    "on": true
  },
  "animation": {
    "function": 0,
    "speed": 1.0,
    "scale": 1.0,
    "palette": 0
  }
}
```

### POST /api/pi/sync
Receives sync data from another Pi. Body is the same as `/api/pi/state`.

### GET /api/pi/discover
Returns list of all discovered Pis:
```json
{
  "devices": [
    {
      "name": "Living Room LEDs._ledcontrol._tcp.local.",
      "device_name": "Living Room LEDs",
      "hostname": "raspberrypi.local",
      "port": 80,
      "addresses": ["192.168.1.100"],
      "group": "living-room",
      "version": "2.0.0",
      "url": "http://192.168.1.100:80",
      "online": true,
      "last_seen": 1234567890.0
    }
  ],
  "count": 1
}
```

### POST /api/pi/sync-to
Sync current state to a specific Pi:
```json
{
  "url": "http://192.168.1.100:80"
}
```

### POST /api/pi/sync-all
Sync current state to all Pis (optionally filtered by group):
```json
{
  "group": "living-room"  // Optional
}
```

### GET/POST /api/pi/settings
Get or update Pi discovery settings:
```json
{
  "device_name": "Living Room LEDs",
  "group": "living-room",
  "master_mode": false
}
```

## WebSocket Events

### Namespace: /discovery

#### Client → Server
- `connect`: Client connects to discovery namespace
- `disconnect`: Client disconnects
- `request_devices`: Request updated device list

#### Server → Client
- `devices_list`: Full list of discovered devices
- `pi_discovered`: New Pi discovered
- `pi_removed`: Pi went offline

## Configuration

Pi settings are saved in the main configuration file (e.g., `/etc/ledcontrol.json`):

```json
{
  "pi_device_name": "Living Room LEDs",
  "pi_group": "living-room",
  "pi_master_mode": false,
  ...
}
```

## Usage

1. **Configure Each Pi**:
   - Go to Discovery page
   - Set a friendly device name
   - Optionally assign a group (e.g., "living-room", "bedroom")
   - Enable Master Mode if you want changes to auto-sync

2. **Sync Settings**:
   - View all discovered Pis on the Discovery page
   - Click "Sync to This Pi" to copy your current settings to another Pi
   - Click "Sync to All" to sync to all Pis (or all in the selected group)

3. **Navigate Between Pis**:
   - Click "Open Web Interface" to jump to another Pi's control page

4. **Master Mode**:
   - When enabled, changes will automatically propagate to all Pis in the same group
   - Useful for keeping multiple LED strips in sync

## Dependencies

- `zeroconf>=0.132.0`: mDNS/Bonjour service discovery
- `requests>=2.28.0`: HTTP client for Pi-to-Pi communication
- `flask-socketio>=5.3.0`: WebSocket support (already required for visualizer)

## Security Note

This feature is designed for use on trusted local networks only. There is no authentication between Pis. For future versions, consider:
- TLS/HTTPS for Pi-to-Pi communication
- API tokens or shared secrets
- Firewall rules to restrict access to specific IPs
