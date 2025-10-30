// led-control WS2812B LED Controller Server
// Copyright 2025 jackw01. Released under the MIT License (see LICENSE for details).

export default {
  name: 'DiscoveryPage',
  data() {
    return {
      devices: [],
      piSettings: {
        device_name: '',
        group: '',
        master_mode: false,
      },
      selectedGroup: 'all',
      syncing: false,
      updating: {}, // Track which devices are updating { hostname: true/false }
      socket: null,
    }
  },
  computed: {
    availableGroups() {
      // Extract unique groups from devices
      const groups = new Set(['all']);
      this.devices.forEach(device => {
        if (device.group) groups.add(device.group);
      });
      return Array.from(groups);
    },
    filteredDevices() {
      if (this.selectedGroup === 'all') {
        return this.devices;
      }
      return this.devices.filter(d => d.group === this.selectedGroup);
    },
    onlineDevices() {
      return this.filteredDevices.filter(d => d.online);
    },
    offlineDevices() {
      return this.filteredDevices.filter(d => !d.online);
    },
    devicesNeedingUpdate() {
      // Compare version strings to find devices with different versions
      const localVersion = this.piSettings.version || '';
      return this.onlineDevices.filter(d => d.version !== localVersion);
    }
  },
  methods: {
    async loadPiSettings() {
      try {
        const response = await fetch('/api/pi/settings');
        if (response.ok) {
          this.piSettings = await response.json();
        }
      } catch (e) {
        console.error('Failed to load Pi settings:', e);
      }
    },
    async savePiSettings() {
      try {
        await fetch('/api/pi/settings', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(this.piSettings)
        });
      } catch (e) {
        console.error('Failed to save Pi settings:', e);
      }
    },
    async loadDevices() {
      try {
        const response = await fetch('/api/pi/discover');
        if (response.ok) {
          const data = await response.json();
          this.devices = data.devices || [];
        }
      } catch (e) {
        console.error('Failed to load devices:', e);
      }
    },
    async syncTo(device) {
      if (!confirm(`Sync current settings to ${device.device_name}?`)) {
        return;
      }
      
      this.syncing = true;
      try {
        const response = await fetch('/api/pi/sync-to', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ url: device.url })
        });
        
        if (response.ok) {
          alert(`Successfully synced to ${device.device_name}`);
        } else {
          const error = await response.json();
          alert(`Failed to sync: ${error.message}`);
        }
      } catch (e) {
        alert(`Failed to sync: ${e.message}`);
      }
      this.syncing = false;
    },
    async syncToAll() {
      const targetGroup = this.selectedGroup === 'all' ? null : this.selectedGroup;
      const groupText = targetGroup ? ` in group "${targetGroup}"` : '';
      
      if (!confirm(`Sync current settings to all Pis${groupText}?`)) {
        return;
      }
      
      this.syncing = true;
      try {
        const response = await fetch('/api/pi/sync-all', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ group: targetGroup })
        });
        
        if (response.ok) {
          const result = await response.json();
          let msg = `Synced to ${result.synced} of ${result.total} Pis`;
          if (result.failed > 0) {
            msg += `\nFailed: ${result.failed_devices.join(', ')}`;
          }
          alert(msg);
        } else {
          const error = await response.json();
          alert(`Failed to sync: ${error.message}`);
        }
      } catch (e) {
        alert(`Failed to sync: ${e.message}`);
      }
      this.syncing = false;
    },
    async updatePi(device, restart = false) {
      const action = restart ? 'update and restart' : 'update';
      if (!confirm(`${action} ${device.device_name || device.hostname}?`)) {
        return;
      }
      
      this.$set(this.updating, device.hostname, true);
      try {
        const response = await fetch('/api/pi/update-remote', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ 
            url: device.url,
            restart: restart
          })
        });
        
        if (response.ok) {
          const result = await response.json();
          if (result.success) {
            let msg = `Successfully updated ${device.device_name}\n`;
            msg += `Version: ${result.old_version} → ${result.new_version}\n`;
            if (result.changes && result.changes.length > 0) {
              msg += `\nChanges:\n${result.changes.join('\n')}`;
            }
            if (restart) {
              msg += '\n\nDevice is restarting...';
            }
            alert(msg);
          } else {
            alert(`Update failed: ${result.message}`);
          }
        } else {
          const error = await response.json();
          alert(`Failed to update: ${error.message}`);
        }
      } catch (e) {
        alert(`Failed to update: ${e.message}`);
      }
      this.$set(this.updating, device.hostname, false);
    },
    async updateAllPis(restart = false) {
      const targetGroup = this.selectedGroup === 'all' ? null : this.selectedGroup;
      const groupText = targetGroup ? ` in group "${targetGroup}"` : '';
      const action = restart ? 'update and restart' : 'update';
      
      if (!confirm(`${action} all Pis${groupText}?`)) {
        return;
      }
      
      this.syncing = true;
      let succeeded = 0;
      let failed = 0;
      const results = [];
      
      for (const device of this.onlineDevices) {
        this.$set(this.updating, device.hostname, true);
        try {
          const response = await fetch('/api/pi/update-remote', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
              url: device.url,
              restart: restart
            })
          });
          
          if (response.ok) {
            const result = await response.json();
            if (result.success) {
              succeeded++;
              results.push(`✓ ${device.device_name}: ${result.old_version} → ${result.new_version}`);
            } else {
              failed++;
              results.push(`✗ ${device.device_name}: ${result.message}`);
            }
          } else {
            failed++;
            results.push(`✗ ${device.device_name}: HTTP ${response.status}`);
          }
        } catch (e) {
          failed++;
          results.push(`✗ ${device.device_name}: ${e.message}`);
        }
        this.$set(this.updating, device.hostname, false);
      }
      
      this.syncing = false;
      
      let msg = `Update Complete\n\nSucceeded: ${succeeded}\nFailed: ${failed}\n\n`;
      msg += results.join('\n');
      alert(msg);
    },
    async restartPi(device) {
      if (!confirm(`Restart ${device.device_name || device.hostname}?`)) {
        return;
      }
      
      this.$set(this.updating, device.hostname, true);
      try {
        const response = await fetch('/api/pi/restart-remote', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ url: device.url })
        });
        
        if (response.ok) {
          alert(`${device.device_name} is restarting...`);
        } else {
          const error = await response.json();
          alert(`Failed to restart: ${error.message}`);
        }
      } catch (e) {
        alert(`Failed to restart: ${e.message}`);
      }
      this.$set(this.updating, device.hostname, false);
    },
    needsUpdate(device) {
      const localVersion = this.piSettings.version || '';
      return device.version !== localVersion;
    },
    jumpToPi(device) {
      window.open(device.url, '_blank');
    },
    getStatusClass(device) {
      return device.online ? 'online' : 'offline';
    },
    getStatusText(device) {
      if (device.online) {
        return 'Online';
      }
      const timeSince = Math.floor((Date.now() / 1000) - device.last_seen);
      return `Offline (${timeSince}s ago)`;
    },
    connectWebSocket() {
      // io is loaded globally from CDN
      this.socket = window.io('/discovery');
      
      this.socket.on('connect', () => {
        console.log('Discovery WebSocket connected');
        this.socket.emit('request_devices');
      });
      
      this.socket.on('devices_list', (data) => {
        console.log('Received devices list:', data);
        this.devices = data.devices || [];
      });
      
      this.socket.on('pi_discovered', (device) => {
        console.log('Pi discovered:', device);
        // Update or add device
        const index = this.devices.findIndex(d => d.name === device.name);
        if (index >= 0) {
          this.devices[index] = device;
        } else {
          this.devices.push(device);
        }
      });
      
      this.socket.on('pi_removed', (device) => {
        console.log('Pi removed:', device);
        const index = this.devices.findIndex(d => d.name === device.name);
        if (index >= 0) {
          this.devices[index].online = false;
        }
      });
      
      this.socket.on('disconnect', () => {
        console.log('Discovery WebSocket disconnected');
      });
    }
  },
  async mounted() {
    await this.loadPiSettings();
    await this.loadDevices();
    this.connectWebSocket();
  },
  beforeUnmount() {
    if (this.socket) {
      this.socket.disconnect();
    }
  },
  template: `
<div class="page">
  <h1>Raspberry Pi Discovery</h1>
  
  <!-- This Pi Settings Card -->
  <div class="card">
    <h2>This Pi Settings</h2>
    <div class="form-group">
      <label>Device Name:</label>
      <input 
        v-model="piSettings.device_name" 
        @change="savePiSettings"
        type="text" 
        placeholder="My LED Controller"
      />
    </div>
    <div class="form-group">
      <label>Group:</label>
      <input 
        v-model="piSettings.group" 
        @change="savePiSettings"
        type="text" 
        placeholder="living-room"
      />
    </div>
    <div class="form-group checkbox-group">
      <label>
        <input 
          v-model="piSettings.master_mode" 
          @change="savePiSettings"
          type="checkbox"
        />
        Master Mode (auto-sync to other Pis)
      </label>
      <p class="help-text">When enabled, changes will automatically sync to all Pis in the same group</p>
    </div>
  </div>
  
  <!-- Filter and Sync Controls -->
  <div class="card">
    <div class="controls-row">
      <div class="form-group">
        <label>Filter by Group:</label>
        <select v-model="selectedGroup">
          <option v-for="group in availableGroups" :key="group" :value="group">
            {{ group === 'all' ? 'All Groups' : group }}
          </option>
        </select>
      </div>
      <div class="button-group">
        <button 
          @click="syncToAll" 
          :disabled="syncing || onlineDevices.length === 0"
          class="btn btn-primary"
        >
          <span v-if="syncing">Syncing...</span>
          <span v-else>Sync to All ({{ onlineDevices.length }})</span>
        </button>
        <button 
          @click="updateAllPis(false)" 
          :disabled="syncing || onlineDevices.length === 0"
          class="btn btn-warning"
        >
          Update All ({{ onlineDevices.length }})
        </button>
        <button 
          @click="updateAllPis(true)" 
          :disabled="syncing || onlineDevices.length === 0"
          class="btn btn-warning"
        >
          Update All & Restart
        </button>
      </div>
    </div>
  </div>
  
  <!-- Discovered Pis -->
  <div class="card">
    <h2>Discovered Raspberry Pis ({{ onlineDevices.length }} online)</h2>
    
    <div v-if="devices.length === 0" class="empty-state">
      <p>No other Pis discovered on the network.</p>
      <p class="help-text">Make sure other Pis are running led-control and are on the same network.</p>
    </div>
    
    <div v-else class="pi-grid">
      <!-- Online Devices -->
      <div 
        v-for="device in onlineDevices" 
        :key="device.name" 
        class="pi-card online"
      >
        <div class="pi-header">
          <h3>{{ device.device_name || device.hostname }}</h3>
          <div class="header-badges">
            <span class="status-badge online">● Online</span>
            <span v-if="needsUpdate(device)" class="status-badge update-available">
              Update Available
            </span>
            <span v-if="updating[device.hostname]" class="status-badge updating">
              ⟳ Updating...
            </span>
          </div>
        </div>
        
        <div class="pi-info">
          <div class="info-row">
            <span class="label">IP:</span>
            <span class="value">{{ device.addresses[0] }}</span>
          </div>
          <div class="info-row">
            <span class="label">Hostname:</span>
            <span class="value">{{ device.hostname }}</span>
          </div>
          <div class="info-row" v-if="device.group">
            <span class="label">Group:</span>
            <span class="value group-tag">{{ device.group }}</span>
          </div>
          <div class="info-row">
            <span class="label">Version:</span>
            <span class="value" :class="{ 'version-outdated': needsUpdate(device) }">
              {{ device.version }}
            </span>
          </div>
        </div>
        
        <div class="pi-actions">
          <button @click="jumpToPi(device)" class="btn btn-secondary">
            Open Web Interface
          </button>
          <button 
            @click="syncTo(device)" 
            :disabled="syncing || updating[device.hostname]"
            class="btn btn-primary"
          >
            Sync Settings
          </button>
          <button 
            @click="updatePi(device, false)" 
            :disabled="updating[device.hostname]"
            class="btn btn-warning"
          >
            Update
          </button>
          <button 
            @click="updatePi(device, true)" 
            :disabled="updating[device.hostname]"
            class="btn btn-warning"
          >
            Update & Restart
          </button>
          <button 
            @click="restartPi(device)" 
            :disabled="updating[device.hostname]"
            class="btn btn-danger"
          >
            Restart
          </button>
        </div>
      </div>
      
      <!-- Offline Devices -->
      <div 
        v-for="device in offlineDevices" 
        :key="device.name" 
        class="pi-card offline"
      >
        <div class="pi-header">
          <h3>{{ device.device_name || device.hostname }}</h3>
          <span class="status-badge offline">● {{ getStatusText(device) }}</span>
        </div>
        
        <div class="pi-info">
          <div class="info-row">
            <span class="label">Last IP:</span>
            <span class="value">{{ device.addresses[0] }}</span>
          </div>
          <div class="info-row" v-if="device.group">
            <span class="label">Group:</span>
            <span class="value group-tag">{{ device.group }}</span>
          </div>
        </div>
        
        <div class="pi-actions">
          <button disabled class="btn btn-secondary">Offline</button>
        </div>
      </div>
    </div>
  </div>
</div>
`
};
