// led-control WS2812B LED Controller Server
// Copyright 2022 jackw01. Released under the MIT License (see LICENSE for details).

import store from '../Store.js';

export default {
  name: 'ControlPage',
  data() {
    return {
      presetKey: '',
      presetSavedKey: 0,
      presetLoaded: false,
    }
  },
  computed: {
    brightnessLimit: function() {
      return store.get('global_brightness_limit');
    },
    groups: function() {
      return store.get('groups');
    },
    orderedGroups: function() {
      return _.fromPairs(_.sortBy(_.toPairs(this.groups), (g) => {
        return g[1].range_start;
      }));
    },
    presets: function() {
      return store.getPresets();
    }
  },
  methods: {
    savePreset() {
      if (this.presetKey === '') alert('Please enter a name for this preset.')
      else {
        this.presetLoaded = true;
        store.savePreset(this.presetKey);
        this.presetSavedKey++;
      }
    },
    deletePreset() {
      if (confirm(`Delete preset "${this.presetKey}?"`)) {
        store.removePreset(this.presetKey);
        this.presetKey = '';
        this.presetLoaded = false;
      }
    },
    loadPreset() {
      this.presetLoaded = true;
      store.loadPreset(this.presetKey);
    }
  },
  template: `
    <div class="control-page">
      <!-- Global Controls Card -->
      <div class="card global-controls-card">
        <div class="card-header">
          <svg class="card-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M12 2v4m0 12v4M4.93 4.93l2.83 2.83m8.48 8.48l2.83 2.83M2 12h4m12 0h4M4.93 19.07l2.83-2.83m8.48-8.48l2.83-2.83"/>
          </svg>
          <h3 class="card-title">Global Controls</h3>
        </div>
        <div class="card-body">
          <slider-number-input
            path="global_brightness"
            label="Brightness"
            unit=""
            v-bind:min="0"
            v-bind:max="brightnessLimit"
            v-bind:step="0.01"
          ></slider-number-input>
          <slider-number-input
            path="global_saturation"
            label="Saturation"
            unit=""
            v-bind:min="0"
            v-bind:max="1"
            v-bind:step="0.01"
          ></slider-number-input>
        </div>
      </div>

      <!-- Presets Card -->
      <div class="card presets-card">
        <div class="card-header">
          <svg class="card-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"></path>
          </svg>
          <h3 class="card-title">Presets</h3>
        </div>
        <div class="card-body">
          <div class="preset-controls">
            <div class="input-group">
              <label class="input-label">Select Preset</label>
              <select
                class="select-modern"
                autocomplete="off"
                v-model="presetKey"
                @change="loadPreset"
              >
                <option value="" disabled>Choose a preset...</option>
                <option
                  v-for="(p, id) in presets"
                  v-bind:value="id"
                  :key="id + presetSavedKey"
                >
                  {{ id }}
                </option>
              </select>
            </div>
            <div class="input-group">
              <label class="input-label">Preset Name</label>
              <input
                type="text"
                class="input-modern"
                v-model="presetKey"
                placeholder="Enter preset name..."
                autocomplete="off"
              >
            </div>
            <div class="button-group">
              <button
                class="btn btn-primary"
                @click="savePreset"
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"></path>
                  <polyline points="17 21 17 13 7 13 7 21"></polyline>
                  <polyline points="7 3 7 8 15 8"></polyline>
                </svg>
                Save Preset
              </button>
              <button
                class="btn btn-danger"
                @click="deletePreset"
                v-show="presetLoaded"
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <polyline points="3 6 5 6 21 6"></polyline>
                  <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                </svg>
                Delete
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Groups -->
      <div class="groups-container">
        <div v-for="(group, k, i) in orderedGroups" :key="k" class="group-card-wrapper">
          <div class="card group-card">
            <div class="card-header">
              <div class="card-header-left">
                <svg class="card-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <rect x="3" y="3" width="7" height="7"></rect>
                  <rect x="14" y="3" width="7" height="7"></rect>
                  <rect x="14" y="14" width="7" height="7"></rect>
                  <rect x="3" y="14" width="7" height="7"></rect>
                </svg>
                <h4 class="card-title">{{ group.name }}</h4>
                <span class="card-badge">Group {{ i + 1 }}</span>
              </div>
            </div>
            <div class="card-body">
              <group-controls
                v-bind:name="k"
                :key="presetKey"
              ></group-controls>
            </div>
          </div>
        </div>
      </div>
    </div>
  `
}
