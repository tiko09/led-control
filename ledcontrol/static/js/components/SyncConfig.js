// led-control WS2812B LED Controller Server
// Copyright 2025 jackw01. Released under the MIT License (see LICENSE for details).

export default {
  name: 'SyncConfig',
  data() {
    return {
      form: {
        enable_sync: false,
        sync_master_mode: false,
        sync_interval: 0.5,
      },
      stats: {
        packets_sent: 0,
        packets_received: 0,
        last_sync_time: null,
      },
      loading: false,
      statsInterval: null,
    };
  },
  mounted() {
    this.load();
    // Auto-refresh stats every 5 seconds
    this.statsInterval = setInterval(() => {
      if (this.form.enable_sync) {
        this.loadStats();
      }
    }, 5000);
  },
  beforeUnmount() {
    if (this.statsInterval) {
      clearInterval(this.statsInterval);
    }
  },
  methods: {
    async load() {
      this.loading = true;
      try {
        const response = await fetch('/api/sync');
        if (response.ok) {
          const data = await response.json();
          this.form = {
            enable_sync: data.enable_sync || false,
            sync_master_mode: data.sync_master_mode || false,
            sync_interval: data.sync_interval || 0.5,
          };
          if (data.stats) {
            this.stats = data.stats;
          }
        }
      } catch (e) {
        console.error('Failed to load sync config:', e);
      } finally {
        this.loading = false;
      }
    },
    async loadStats() {
      try {
        const response = await fetch('/api/sync');
        if (response.ok) {
          const data = await response.json();
          if (data.stats) {
            this.stats = data.stats;
          }
        }
      } catch (e) {
        console.error('Failed to load sync stats:', e);
      }
    },
    async save() {
      this.loading = true;
      try {
        const response = await fetch('/api/sync', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(this.form),
        });
        if (response.ok) {
          alert('Sync settings saved successfully!');
          // Reload stats after save
          await this.load();
        } else {
          alert('Failed to save sync settings');
        }
      } catch (e) {
        console.error('Failed to save sync config:', e);
        alert('Error saving sync settings');
      } finally {
        this.loading = false;
      }
    },
    formatLastSyncTime() {
      if (!this.stats.last_sync_time) return 'Never';
      const date = new Date(this.stats.last_sync_time * 1000);
      const now = new Date();
      const diffMs = now - date;
      const diffSec = Math.floor(diffMs / 1000);
      
      if (diffSec < 60) return `${diffSec}s ago`;
      if (diffSec < 3600) return `${Math.floor(diffSec / 60)}m ago`;
      return date.toLocaleTimeString();
    }
  },
  template: `
<div class="card">
  <h2>Animation Synchronization</h2>
  
  <div class="form-group checkbox-group">
    <label>
      <input 
        v-model="form.enable_sync" 
        type="checkbox"
      />
      Enable Animation Synchronization
    </label>
    <p class="help-text">Synchronize animation timing across multiple Pis in the network</p>
  </div>
  
  <div v-if="form.enable_sync">
    <!-- Mode Selection -->
    <div class="form-group">
      <label>Synchronization Mode:</label>
      <div class="mode-selection">
        <div 
          class="mode-card" 
          :class="{ active: form.sync_master_mode }"
          @click="form.sync_master_mode = true"
        >
          <h4>Master Mode</h4>
          <p>Broadcasts animation time to all Pis in the network</p>
          <div v-if="form.sync_master_mode && stats.packets_sent > 0" class="stats">
            <div class="stat-item">
              <span class="label">Packets Sent:</span>
              <span class="value">{{ stats.packets_sent }}</span>
            </div>
          </div>
        </div>
        
        <div 
          class="mode-card" 
          :class="{ active: !form.sync_master_mode }"
          @click="form.sync_master_mode = false"
        >
          <h4>Slave Mode</h4>
          <p>Receives animation time from master Pi</p>
          <div v-if="!form.sync_master_mode && stats.packets_received > 0" class="stats">
            <div class="stat-item">
              <span class="label">Packets Received:</span>
              <span class="value">{{ stats.packets_received }}</span>
            </div>
            <div class="stat-item" v-if="stats.last_sync_time">
              <span class="label">Last Sync:</span>
              <span class="value">{{ formatLastSyncTime() }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
    
    <!-- Master Settings -->
    <div v-if="form.sync_master_mode" class="form-group">
      <label>Broadcast Interval (seconds):</label>
      <input 
        v-model.number="form.sync_interval" 
        type="number" 
        min="0.1" 
        max="5.0" 
        step="0.1"
      />
      <p class="help-text">How often to broadcast sync packets (0.1 - 5.0 seconds)</p>
    </div>
    
    <!-- Info Box -->
    <div class="info-box">
      <h4>ℹ️ How it works:</h4>
      <ul>
        <li><strong>Master Pi:</strong> Broadcasts current animation time via UDP to all devices on port 6455</li>
        <li><strong>Slave Pis:</strong> Receive time updates and synchronize their animations accordingly</li>
        <li><strong>Same animation required:</strong> All Pis must use the same animation settings for perfect sync</li>
        <li><strong>Network:</strong> All Pis must be on the same network to receive broadcast packets</li>
      </ul>
    </div>
    
    <button 
      @click="save" 
      :disabled="loading"
      class="btn btn-primary"
    >
      {{ loading ? 'Saving...' : 'Save Sync Settings' }}
    </button>
  </div>
</div>
`,
};
