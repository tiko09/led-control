// led-control WS2812B LED Controller Server
// Copyright 2022 jackw01. Released under the MIT License (see LICENSE for details).

import store from '../Store.js';
import ArtnetConfig from '../components/ArtnetConfig.js';

export default {
  name: 'SetupPage',
  components: { ArtnetConfig },
  data() {
    return {
      calibration: store.get('calibration'),
      useWhiteChannel: store.get('use_white_channel'),
      whiteLedTemperature: store.get('white_led_temperature'),
      rgbwAlgorithm: store.get('rgbw_algorithm'),
      groupListKey: 0,
      logLevel: 'INFO',
      logLevels: ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
      saving: false,
    }
  },
  computed: {
    groups: function() {
      return store.get('groups');
    },
    ledStripType: function() {
      return store.get('led_strip_type') || '';
    }
  },
  methods: {
    updateCalibration() {
      store.set('calibration', parseInt(this.calibration, 10));
    },
    updateWhiteChannel() {
      store.set('use_white_channel', this.useWhiteChannel);
    },
    updateWhiteLedTemperature() {
      store.set('white_led_temperature', parseInt(this.whiteLedTemperature, 10));
    },
    updateRgbwAlgorithm() {
      store.set('rgbw_algorithm', this.rgbwAlgorithm);
    },
    async addGroup(key) {
      await store.createGroup(key);
      this.groupListKey++;
    },
    async deleteGroup(key) {
      if (confirm(`Delete group "${this.groups[key].name}?"`)) {
        await store.removeGroup(key);
        this.groupListKey++;
      }
    },
    getOrderedGroups() {
      // Does not work in computed properties
      return _.fromPairs(_.sortBy(_.toPairs(this.groups), (g) => {
        return g[1].range_start;
      }));
    },
    async saveLogLevel() {
      this.saving = true;
      try {
        await fetch('/api/loglevel', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ log_level: this.logLevel })
        });
      } catch (e) {
        console.error('Failed to save log level:', e);
      }
      this.saving = false;
    }
  },
  async mounted() {
    const r = await fetch('/api/loglevel');
    if (r.ok) {
      const j = await r.json();
      this.logLevel = j.log_level || 'INFO';
    }
  },
  template: `
    <div class="page setup-page">
      <!-- Color Calibration Card -->
      <div class="card">
        <div class="card-header">
          <div class="card-header-left">
            <svg class="card-icon" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"></circle>
              <circle cx="12" cy="12" r="4"></circle>
              <line x1="21.17" y1="8" x2="12" y2="8"></line>
              <line x1="3.95" y1="6.06" x2="8.54" y2="14"></line>
              <line x1="10.88" y1="21.94" x2="15.46" y2="14"></line>
            </svg>
            <h2 class="card-title">Color Calibration</h2>
          </div>
        </div>
        <div class="card-body">
          <slider-number-input
            path="global_color_temp"
            label="Global Color Temperature"
            unit="K"
            v-bind:min="1000"
            v-bind:max="12000"
            v-bind:step="50"
          ></slider-number-input>
          <slider-number-input
            path="global_color_r"
            label="Red Channel Correction"
            unit=""
            v-bind:min="0"
            v-bind:max="255"
            v-bind:step="1"
          ></slider-number-input>
          <slider-number-input
            path="global_color_g"
            label="Green Channel Correction"
            unit=""
            v-bind:min="0"
            v-bind:max="255"
            v-bind:step="1"
          ></slider-number-input>
          <slider-number-input
            path="global_color_b"
            label="Blue Channel Correction"
            unit=""
            v-bind:min="0"
            v-bind:max="255"
            v-bind:step="1"
          ></slider-number-input>
          
          <div class="input-group mt-2">
            <label class="input-label">Test Color Correction</label>
            <select
              class="select-modern"
              autocomplete="off"
              v-model="calibration"
              @change="updateCalibration"
            >
              <option value="0">Off</option>
              <option value="1">On</option>
            </select>
          </div>
        </div>
      </div>

      <!-- RGBW Settings Card -->
      <div class="card" v-if="ledStripType.includes('W')">
        <div class="card-header">
          <div class="card-header-left">
            <svg class="card-icon" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M12 2v4m0 12v4M4.93 4.93l2.83 2.83m8.48 8.48l2.83 2.83M2 12h4m12 0h4M4.93 19.07l2.83-2.83m8.48-8.48l2.83-2.83"></path>
              <circle cx="12" cy="12" r="3"></circle>
            </svg>
            <h2 class="card-title">RGBW Settings</h2>
          </div>
        </div>
        <div class="card-body">
          <div class="input-group">
            <label class="input-label">
              Use White Channel in Animations
              <span class="input-hint">Enable to use the dedicated white LED during pattern animations. When enabled, colors with low saturation will activate the white channel for better color accuracy and efficiency.</span>
            </label>
            <label class="switch">
              <input
                type="checkbox"
                v-model="useWhiteChannel"
                @change="updateWhiteChannel"
              />
              <span class="slider-switch"></span>
            </label>
          </div>

          <div class="input-group" v-if="useWhiteChannel">
            <label class="input-label">
              RGBW Algorithm
              <span class="input-hint">Legacy: Uses desaturation (current). Advanced: Extracts white from RGB colors for better efficiency.</span>
            </label>
            <select 
              v-model="rgbwAlgorithm" 
              @change="updateRgbwAlgorithm"
              class="input-select"
            >
              <option value="legacy">Legacy (Desaturation)</option>
              <option value="advanced">Advanced (White Extraction)</option>
            </select>
          </div>

          <div class="input-group" v-if="useWhiteChannel && rgbwAlgorithm === 'advanced'">
            <label class="input-label">
              White LED Color Temperature
              <span class="input-hint">Set the color temperature of your white LEDs ({{ whiteLedTemperature }}K). Warmer whites (2700K-3500K) have more red/yellow, cooler whites (5000K-6500K) are more blue. This helps the algorithm accurately convert RGB to RGBW.</span>
            </label>
            <input
              type="range"
              v-model="whiteLedTemperature"
              @input="updateWhiteLedTemperature"
              min="2700"
              max="6500"
              step="100"
              class="slider"
            />
            <div style="display: flex; justify-content: space-between; font-size: 0.85em; color: var(--text-secondary); margin-top: 4px;">
              <span>2700K (Warm)</span>
              <span>4000K (Neutral)</span>
              <span>6500K (Cool)</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Debug Logging Card -->
      <div class="card">
        <div class="card-header">
          <div class="card-header-left">
            <svg class="card-icon" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
              <polyline points="14 2 14 8 20 8"></polyline>
              <line x1="16" y1="13" x2="8" y2="13"></line>
              <line x1="16" y1="17" x2="8" y2="17"></line>
              <polyline points="10 9 9 9 8 9"></polyline>
            </svg>
            <h2 class="card-title">Debug Logging</h2>
          </div>
        </div>
        <div class="card-body">
          <div class="input-group">
            <label class="input-label">Log Level</label>
            <div class="input-with-button">
              <select class="select-modern" v-model="logLevel" @change="saveLogLevel">
                <option v-for="lvl in logLevels" :value="lvl">{{ lvl }}</option>
              </select>
            </div>
            <span class="input-hint">Controls verbosity of server logs (DEBUG = most verbose)</span>
          </div>
        </div>
      </div>

      <!-- LED Groups Configuration -->
      <div class="card">
        <div class="card-header">
          <div class="card-header-left">
            <svg class="card-icon" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="8" y1="6" x2="21" y2="6"></line>
              <line x1="8" y1="12" x2="21" y2="12"></line>
              <line x1="8" y1="18" x2="21" y2="18"></line>
              <line x1="3" y1="6" x2="3.01" y2="6"></line>
              <line x1="3" y1="12" x2="3.01" y2="12"></line>
              <line x1="3" y1="18" x2="3.01" y2="18"></line>
            </svg>
            <h2 class="card-title">LED Groups</h2>
            <span class="card-badge">{{ Object.keys(groups).length }}</span>
          </div>
        </div>
        <div class="card-body">
          <div class="groups-list">
            <div v-for="(group, k, i) in getOrderedGroups()" :key="k + groupListKey" class="group-config-item">
              <div class="group-config-header">
                <h4 class="group-config-title">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <circle cx="12" cy="12" r="3"></circle>
                    <path d="M12 1v6m0 6v6M5.64 5.64l4.24 4.24m4.24 4.24l4.24 4.24M1 12h6m6 0h6M5.64 18.36l4.24-4.24m4.24-4.24l4.24-4.24"></path>
                  </svg>
                  Group {{ i + 1 }} - {{ group.name }}
                </h4>
                <div class="button-group">
                  <button
                    class="btn btn-secondary btn-sm"
                    @click="addGroup(k)"
                  >
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <line x1="12" y1="5" x2="12" y2="19"></line>
                      <line x1="5" y1="12" x2="19" y2="12"></line>
                    </svg>
                    Add
                  </button>
                  <button
                    v-show="k !== 'main'"
                    class="btn btn-danger btn-sm"
                    @click="deleteGroup(k)"
                  >
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <polyline points="3 6 5 6 21 6"></polyline>
                      <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                    </svg>
                    Remove
                  </button>
                </div>
              </div>
              <group-config
                v-bind:name="k"
              ></group-config>
            </div>
          </div>
        </div>
      </div>

      <!-- ArtNet Configuration -->
      <artnet-config></artnet-config>
    </div>
  `,
}
