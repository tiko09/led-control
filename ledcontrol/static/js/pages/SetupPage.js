// led-control WS2812B LED Controller Server
// Copyright 2022 jackw01. Released under the MIT License (see LICENSE for details).

import store from '../Store.js';
import ArtnetConfig from '../components/ArtnetConfig.js';

export default {
  name: 'SetupPage',
  components: { ArtnetConfig },
  data() {
    return {
      sacn: store.get('sacn'),
      calibration: store.get('calibration'),
      groupListKey: 0,
    }
  },
  computed: {
    groups: function() {
      return store.get('groups');
    }
  },
  methods: {
    updateSACN() {
      store.set('sacn', parseInt(this.sacn, 10));
    },
    updateCalibration() {
      store.set('calibration', parseInt(this.calibration, 10));
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

      <!-- Control Protocol Card -->
      <div class="card">
        <div class="card-header">
          <div class="card-header-left">
            <svg class="card-icon" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="2" y="7" width="20" height="14" rx="2" ry="2"></rect>
              <path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"></path>
            </svg>
            <h2 class="card-title">Control Protocol</h2>
          </div>
        </div>
        <div class="card-body">
          <div class="input-group">
            <label class="input-label">E1.31 sACN Control</label>
            <select
              class="select-modern"
              autocomplete="off"
              v-model="sacn"
              @change="updateSACN"
            >
              <option value="0">Off</option>
              <option value="1">On</option>
            </select>
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
