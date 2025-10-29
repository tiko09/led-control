// led-control WS2812B LED Controller Server
// Copyright 2022 jackw01. Released under the MIT License (see LICENSE for details).

import store from '../Store.js';

export default {
  props: {
    'path': String,
    'label': String,
    'unit': String,
    'min': Number,
    'max': Number,
    'step': Number,
  },
  data() {
    return {
      val: store.get(this.path),
    }
  },
  methods: {
    update(event) {
      store.set(this.path, _.clamp(this.val, this.min, this.max));
    }
  },
  template: `
    <div class="slider-number-input">
      <div class="slider-header">
        <label class="slider-label">{{ label }}</label>
        <div class="slider-value-display">
          <span class="slider-value">{{ val }}</span>
          <span class="slider-unit" v-if="unit.length > 0">{{ unit }}</span>
        </div>
      </div>
      <div class="slider-controls">
        <input
          type="range"
          class="slider-input"
          :min="min"
          :max="max"
          :step="step"
          autocomplete="off"
          v-model="val"
          @input="update"
          @change="update"
        >
        <input
          type="number"
          class="number-input"
          :min="min"
          :max="max"
          :step="step"
          autocomplete="off"
          v-model="val"
          @change="update"
        >
      </div>
    </div>
  `,
};
