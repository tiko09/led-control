export default {
    name: 'ArtnetConfig',
    template: `
      <div class="card artnet-config">
        <div class="card-header">
          <div class="card-header-left">
            <svg class="card-icon" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="2" y="2" width="20" height="8" rx="2" ry="2"></rect>
              <rect x="2" y="14" width="20" height="8" rx="2" ry="2"></rect>
              <line x1="6" y1="6" x2="6.01" y2="6"></line>
              <line x1="6" y1="18" x2="6.01" y2="18"></line>
            </svg>
            <h2 class="card-title">ArtNet / sACN Configuration</h2>
          </div>
        </div>
        
        <div class="card-body">
          <div v-if="loading" class="loading-state">
            <svg class="spinner" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="12" y1="2" x2="12" y2="6"></line>
              <line x1="12" y1="18" x2="12" y2="22"></line>
              <line x1="4.93" y1="4.93" x2="7.76" y2="7.76"></line>
              <line x1="16.24" y1="16.24" x2="19.07" y2="19.07"></line>
              <line x1="2" y1="12" x2="6" y2="12"></line>
              <line x1="18" y1="12" x2="22" y2="12"></line>
              <line x1="4.93" y1="19.07" x2="7.76" y2="16.24"></line>
              <line x1="16.24" y1="7.76" x2="19.07" y2="4.93"></line>
            </svg>
            <span>Loading configuration...</span>
          </div>
          
          <div v-else class="artnet-content">
            <!-- Enable Toggle -->
            <div class="artnet-toggle">
              <label class="toggle-label">
                <input type="checkbox" class="toggle-input" v-model="form.enable_artnet">
                <span class="toggle-slider"></span>
                <span class="toggle-text">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"></path>
                  </svg>
                  ArtNet Mode {{ form.enable_artnet ? 'Enabled' : 'Disabled' }}
                </span>
              </label>
            </div>

            <!-- Configuration Sections -->
            <div class="artnet-sections" :class="{ 'disabled': !form.enable_artnet }">
              
              <!-- Connection Settings -->
              <div class="config-section">
                <h4 class="section-subtitle">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <circle cx="12" cy="12" r="10"></circle>
                    <line x1="2" y1="12" x2="22" y2="12"></line>
                    <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path>
                  </svg>
                  Connection Settings
                </h4>
                <div class="config-grid">
                  <div class="input-group">
                    <label class="input-label">Universe</label>
                    <input 
                      type="number" 
                      class="input-modern" 
                      min="0" 
                      max="32767" 
                      v-model.number="form.artnet_universe"
                      :disabled="!form.enable_artnet"
                    >
                    <span class="input-hint">ArtNet universe (0-32767)</span>
                  </div>
                  
                  <div class="input-group">
                    <label class="input-label">Channel Offset</label>
                    <input 
                      type="number" 
                      class="input-modern" 
                      min="0" 
                      max="511" 
                      v-model.number="form.artnet_channel_offset"
                      :disabled="!form.enable_artnet"
                    >
                    <span class="input-hint">Starting DMX channel (0-511)</span>
                  </div>
                  
                  <div class="input-group">
                    <label class="input-label">LEDs per Pixel</label>
                    <input 
                      type="number" 
                      class="input-modern" 
                      min="1" 
                      max="1024" 
                      v-model.number="form.artnet_group_size"
                      :disabled="!form.enable_artnet"
                    >
                    <span class="input-hint">Pixel grouping size (1-1024)</span>
                  </div>
                </div>
              </div>

              <!-- Frame Interpolation -->
              <div class="config-section">
                <h4 class="section-subtitle">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline>
                  </svg>
                  Frame Interpolation
                </h4>
                <div class="config-grid">
                  <div class="input-group">
                    <label class="input-label">Interpolation Method</label>
                    <select 
                      class="select-modern" 
                      v-model="form.artnet_frame_interpolation"
                      :disabled="!form.enable_artnet"
                    >
                      <option value="none">None</option>
                      <option value="average">Moving Average</option>
                      <option value="lerp">Linear Interpolation</option>
                    </select>
                    <span class="input-hint">Smooth transitions between frames</span>
                  </div>
                  
                  <div class="input-group">
                    <label class="input-label">Window Size</label>
                    <input 
                      type="number" 
                      class="input-modern" 
                      min="1" 
                      max="20" 
                      v-model.number="form.artnet_frame_interp_size"
                      :disabled="!form.enable_artnet || form.artnet_frame_interpolation === 'none'"
                    >
                    <span class="input-hint">Number of frames to interpolate (1-20)</span>
                  </div>
                </div>
              </div>

              <!-- Spatial Smoothing -->
              <div class="config-section">
                <h4 class="section-subtitle">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path>
                    <polyline points="7.5 4.21 12 6.81 16.5 4.21"></polyline>
                    <polyline points="7.5 19.79 7.5 14.6 3 12"></polyline>
                    <polyline points="21 12 16.5 14.6 16.5 19.79"></polyline>
                    <polyline points="3.27 6.96 12 12.01 20.73 6.96"></polyline>
                    <line x1="12" y1="22.08" x2="12" y2="12"></line>
                  </svg>
                  Spatial Smoothing
                </h4>
                <div class="config-grid">
                  <div class="input-group">
                    <label class="input-label">Smoothing Method</label>
                    <select 
                      class="select-modern" 
                      v-model="form.artnet_spatial_smoothing"
                      :disabled="!form.enable_artnet"
                    >
                      <option value="none">None</option>
                      <option value="average">Moving Average</option>
                      <option value="lerp">Linear Interpolation</option>
                      <option value="gaussian">Gaussian Blur</option>
                    </select>
                    <span class="input-hint">Smooth colors across LEDs</span>
                  </div>
                  
                  <div class="input-group">
                    <label class="input-label">Window Size</label>
                    <input 
                      type="number" 
                      class="input-modern" 
                      min="1" 
                      max="20" 
                      v-model.number="form.artnet_spatial_size"
                      :disabled="!form.enable_artnet || form.artnet_spatial_smoothing === 'none'"
                    >
                    <span class="input-hint">Smoothing kernel size (1-20)</span>
                  </div>
                </div>
              </div>

              <!-- Capacity Info -->
              <div class="info-box">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <circle cx="12" cy="12" r="10"></circle>
                  <line x1="12" y1="16" x2="12" y2="12"></line>
                  <line x1="12" y1="8" x2="12.01" y2="8"></line>
                </svg>
                <div class="info-content">
                  <div class="info-label">Effective Physical Capacity</div>
                  <div class="info-value">
                    {{ Math.floor((512 - form.artnet_channel_offset)/4) * form.artnet_group_size }} LEDs
                    <span class="info-detail">
                      (controlled by {{ Math.ceil( form.artnet_group_size>0 ? form.artnet_group_size : 1 )}}-LED groups)
                    </span>
                  </div>
                </div>
              </div>

              <!-- Logging -->
              <div class="config-section">
                <h4 class="section-subtitle">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                    <polyline points="14 2 14 8 20 8"></polyline>
                    <line x1="16" y1="13" x2="8" y2="13"></line>
                    <line x1="16" y1="17" x2="8" y2="17"></line>
                    <polyline points="10 9 9 9 8 9"></polyline>
                  </svg>
                  Debug Logging
                </h4>
                <div class="config-grid">
                  <div class="input-group">
                    <label class="input-label">Log Level</label>
                    <div class="input-with-button">
                      <select class="select-modern" v-model="logLevel">
                        <option v-for="lvl in logLevels" :value="lvl">{{ lvl }}</option>
                      </select>
                      <button 
                        class="btn btn-secondary btn-sm" 
                        @click="saveLogLevel" 
                        :disabled="saving"
                      >
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                          <polyline points="20 6 9 17 4 12"></polyline>
                        </svg>
                        Apply
                      </button>
                    </div>
                    <span class="input-hint">Set logging verbosity level</span>
                  </div>
                </div>
              </div>
            </div>

            <!-- Action Buttons -->
            <div class="artnet-actions">
              <button 
                class="btn btn-primary" 
                @click="save" 
                :disabled="saving || !form.enable_artnet"
              >
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"></path>
                  <polyline points="17 21 17 13 7 13 7 21"></polyline>
                  <polyline points="7 3 7 8 15 8"></polyline>
                </svg>
                {{ saving ? 'Saving...' : 'Save Configuration' }}
              </button>
              
              <button 
                class="btn btn-secondary" 
                @click="load" 
                :disabled="saving"
              >
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <polyline points="23 4 23 10 17 10"></polyline>
                  <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"></path>
                </svg>
                Reload
              </button>
              
              <div v-if="message" class="status-message" :class="messageType">
                <svg v-if="messageType === 'ok'" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
                  <polyline points="22 4 12 14.01 9 11.01"></polyline>
                </svg>
                <svg v-else width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <circle cx="12" cy="12" r="10"></circle>
                  <line x1="12" y1="8" x2="12" y2="12"></line>
                  <line x1="12" y1="16" x2="12.01" y2="16"></line>
                </svg>
                {{ message }}
              </div>
            </div>
          </div>
        </div>
      </div>
    `,
    data() {
      return {
        loading: true,
        saving: false,
        message: '',
        messageType: 'ok',
        form: {
          enable_artnet: false,
          artnet_universe: 0,
          artnet_channel_offset: 0,
          artnet_group_size: 1,
          artnet_frame_interpolation: "none",
          artnet_frame_interp_size: 2,
          artnet_spatial_smoothing: "none",
          artnet_spatial_size: 1,
        },
        logLevel: "INFO",
        logLevels: ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
      };
    },
    methods: {
      async load() {
        this.loading = true;
        this.message = '';
        try {
          const r = await fetch('/api/artnet');
          if (!r.ok) throw new Error('HTTP '+r.status);
          const j = await r.json();
          this.form.enable_artnet = !!j.enable_artnet;
          this.form.artnet_universe = j.artnet_universe ?? 0;
          this.form.artnet_channel_offset = j.artnet_channel_offset ?? 0;
          this.form.artnet_group_size = j.artnet_group_size ?? 1;
          this.form.artnet_smoothing = j.artnet_smoothing ?? "none";
          this.form.artnet_frame_interpolation = j.artnet_frame_interpolation ?? "none";
          this.form.artnet_frame_interp_size = j.artnet_frame_interp_size ?? 2;
          this.form.artnet_spatial_smoothing = j.artnet_spatial_smoothing ?? "none";
          this.form.artnet_spatial_size = j.artnet_spatial_size ?? 1;
        } catch (e) {
          this.message = 'Laden fehlgeschlagen';
          this.messageType = 'error';
        } finally {
          this.loading = false;
        }
      },
      async save() {
        this.saving = true;
        this.message = '';
        try {
          const r = await fetch('/api/artnet', {
            method: 'POST',
              headers: {'Content-Type':'application/json'},
              body: JSON.stringify(this.form)
          });
          if (!r.ok) throw new Error('HTTP '+r.status);
          this.message = 'Gespeichert';
          this.messageType = 'ok';
        } catch (e) {
          this.message = 'Speichern fehlgeschlagen';
          this.messageType = 'error';
        } finally {
          this.saving = false;
        }
      },
      async saveLogLevel() {
        this.saving = true;
        try {
          await fetch('/api/loglevel', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ log_level: this.logLevel })
          });
          this.message = "Log-Level gespeichert";
          this.messageType = "ok";
        } catch (e) {
          this.message = "Fehler beim Speichern des Log-Levels";
          this.messageType = "error";
        }
        this.saving = false;
      },
    },
    async mounted() {
      this.load();
      const r = await fetch('/api/loglevel');
      if (r.ok) {
        const j = await r.json();
        this.logLevel = j.log_level || "INFO";
      }
    }
  };