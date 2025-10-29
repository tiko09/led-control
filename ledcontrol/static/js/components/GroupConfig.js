// led-control WS2812B LED Controller Server
// Copyright 2022 jackw01. Released under the MIT License (see LICENSE for details).

import store from '../Store.js';

export default {
  props: {
    'name': String,
  },
  data() {
    return {
      group: store.get('groups')[this.name],
    }
  },
  methods: {
    rename(event) {
      store.set(`groups[${this.name}].name`, this.group.name);
    },
    setTarget(event) {
      const items = {};
      items[`groups[${this.name}].render_mode`] = this.group.render_mode;
      items[`groups[${this.name}].render_target`] = this.group.render_target;
      store.setMultiple(items);
    },
    setBounds(event) {
      if (this.group.range_start < this.group.range_end) {
        const items = {};
        items[`groups[${this.name}].range_start`] = this.group.range_start;
        items[`groups[${this.name}].range_end`] = this.group.range_end;
        store.setMultiple(items);
      }
    }
  },
  template: `
    <div class="group-config-form">
      <!-- Group Name -->
      <div class="input-group">
        <label class="input-label">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"></path>
            <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"></path>
          </svg>
          Group Name
        </label>
        <input
          type="text"
          class="input-modern"
          autocomplete="off"
          placeholder="Enter group name"
          v-model="group.name"
          @change="rename"
        >
      </div>

      <!-- Render Mode -->
      <div class="input-group">
        <label class="input-label">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="2" y="3" width="20" height="14" rx="2" ry="2"></rect>
            <line x1="8" y1="21" x2="16" y2="21"></line>
            <line x1="12" y1="17" x2="12" y2="21"></line>
          </svg>
          Render Mode
        </label>
        <select
          class="select-modern"
          autocomplete="off"
          v-model="group.render_mode"
          @change="setTarget"
        >
          <option value="local">
            🖥️ Local (Raspberry Pi)
          </option>
          <option value="serial">
            🔌 Serial (Raspberry Pi Pico)
          </option>
          <option value="udp">
            📡 WiFi (Raspberry Pi Pico W)
          </option>
        </select>
      </div>

      <!-- Render Target (conditional) -->
      <div class="input-group" v-if="group.render_mode !== 'local'">
        <label class="input-label">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"></circle>
            <line x1="2" y1="12" x2="22" y2="12"></line>
            <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path>
          </svg>
          Render Target
          <span class="label-badge">{{ group.render_mode === 'serial' ? 'Port' : 'Hostname' }}</span>
        </label>
        <input
          type="text"
          class="input-modern"
          autocomplete="off"
          :placeholder="group.render_mode === 'serial' ? '/dev/ttyACM0' : 'pico-w.local'"
          v-model="group.render_target"
          @change="setTarget"
        >
        <span class="input-hint">
          {{ group.render_mode === 'serial' ? 'Serial port path (e.g., /dev/ttyACM0)' : 'Network hostname or IP address' }}
        </span>
      </div>

      <!-- LED Range -->
      <div class="input-group">
        <label class="input-label">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="8" y1="6" x2="21" y2="6"></line>
            <line x1="8" y1="12" x2="21" y2="12"></line>
            <line x1="8" y1="18" x2="21" y2="18"></line>
            <line x1="3" y1="6" x2="3.01" y2="6"></line>
            <line x1="3" y1="12" x2="3.01" y2="12"></line>
            <line x1="3" y1="18" x2="3.01" y2="18"></line>
          </svg>
          LED Range
          <span class="label-badge">{{ group.range_end - group.range_start }} LEDs</span>
        </label>
        <div class="range-inputs">
          <div class="range-input-wrapper">
            <span class="range-label">Start</span>
            <input
              type="number"
              class="input-modern input-compact"
              min="0"
              max="10000"
              step="1"
              autocomplete="off"
              v-model.number="group.range_start"
              @change="setBounds"
            >
          </div>
          <svg class="range-arrow" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="5" y1="12" x2="19" y2="12"></line>
            <polyline points="12 5 19 12 12 19"></polyline>
          </svg>
          <div class="range-input-wrapper">
            <span class="range-label">End</span>
            <input
              type="number"
              class="input-modern input-compact"
              min="0"
              max="10000"
              step="1"
              autocomplete="off"
              v-model.number="group.range_end"
              @change="setBounds"
            >
          </div>
        </div>
        <span class="input-hint">
          Define the LED strip range for this group (0-based indexing)
        </span>
      </div>
    </div>
  `,
};
