// led-control WS2812B LED Controller Server
// Copyright 2022 jackw01. Released under the MIT License (see LICENSE for details).

import store from '../Store.js';

export default {
  props: {
    'name': String,
  },
  data() {
    const functionKey = store.get('groups.' + this.name + '.function');
    const paletteKey = store.get('groups.' + this.name + '.palette');
    return {
      functionKey,
      animFunction: store.getFunctions()[functionKey],
      sourceStatus: '',
      sourceStatusClass: '',
      paletteKey,
      palette: store.getPalettes()[paletteKey],
      codeMirror: {},
      palettePreviewKey: 0,
      showPaletteList: false,
    }
  },
  computed: {
    groups: function() {
      return store.get('groups');
    },
    functions: function() {
      return store.getFunctions();
    },
    palettes: function() {
      return store.getPalettes();
    },
  },
  methods: {
    updateFunction() {
      store.set('groups.' + this.name + '.function', parseInt(this.functionKey, 10));
      this.animFunction = this.functions[this.functionKey];
      this.$nextTick(this.createCodeEditor);
    },
    async updateFunctionSource() {
      await store.setFunction(parseInt(this.functionKey, 10), this.animFunction);
    },
    newFunction() {
      const newKey = Date.now();
      const newFunction = JSON.parse(JSON.stringify(this.animFunction));
      newFunction.name = this.animFunction.name + ' (Copy)';
      newFunction.default = false;
      store.setFunction(newKey, newFunction);
      this.functionKey = newKey;
      this.updateFunction();
    },
    deleteFunction() {
      if (confirm(`Delete pattern "${this.animFunction.name}?"`)) {
        store.removeFunction(parseInt(this.functionKey, 10));
        this.functionKey = 0;
        this.updateFunction();
      }
    },
    async compileFunction() {
      const source = this.codeMirror.getValue();
      this.animFunction.source = source;
      await this.updateFunctionSource();
      const result = await store.requestCompile(parseInt(this.functionKey, 10));
      if (result.errors.length === 0) {
        this.sourceStatusClass = 'status-success';
        this.sourceStatus = 'Pattern compiled successfully';
      } else if (result.errors.length > 0) {
        this.sourceStatusClass = 'status-error';
        this.sourceStatus = result.errors.join(', ');
      }
    },
    createCodeEditor() {
      let code = this.animFunction.source.trim();
      if (this.animFunction.default) {
        code = '# Editing and renaming disabled on default patterns. Click "New Pattern" to create and edit a copy of this pattern.\n\n' + code;
      }
      this.codeMirror = new CodeMirror(this.$refs.code, {
        value: code,
        mode: 'python',
        indentUnit: 4,
        lineNumbers: true,
        lineWrapping: true,
        theme: 'summer-night',
        readOnly: this.animFunction.default,
      });
      this.codeMirror.setOption('extraKeys', {
        Tab: function(cm) {
          const spaces = Array(cm.getOption('indentUnit') + 1).join(' ');
          cm.replaceSelection(spaces);
        }
      });
      this.sourceStatus = 'Pattern not compiled yet';
      this.sourceStatusClass = 'status-none';
    },
    updatePalette() {
      store.set('groups.' + this.name + '.palette', parseInt(this.paletteKey, 10));
      this.palette = this.palettes[this.paletteKey];
      this.palettePreviewKey++;
      this.$nextTick(this.createColorPickers);
    },
    selectPalette(id) {
      this.paletteKey = id;
      this.updatePalette();
    },
    newPalette() {
      const newKey = Date.now();
      const newPalette = JSON.parse(JSON.stringify(this.palette));
      newPalette.name = this.palette.name + ' (Copy)';
      newPalette.default = false;
      store.setPalette(newKey, newPalette);
      this.paletteKey = newKey;
      this.updatePalette();
    },
    deletePalette() {
      if (confirm(`Delete palette "${this.palette.name}?"`)) {
        store.removePalette(parseInt(this.paletteKey, 10));
        this.paletteKey = 0;
        this.updatePalette();
      }
    },
    updatePaletteContents() {
      store.setPalette(parseInt(this.paletteKey, 10), this.palette);
      this.palettePreviewKey++;
    },
    addColor(i) {
      this.palette.colors.splice(i + 1, 0, this.palette.colors[i].slice());
      this.updatePaletteContents();
      this.$nextTick(this.createColorPickers);
    },
    deleteColor(i) {
      if (this.palette.colors.length > 2) {
        this.palette.colors.splice(i, 1);
        this.updatePaletteContents();
        this.$nextTick(this.createColorPickers);
      }
    },
    togglePaletteList() {
      this.showPaletteList = !this.showPaletteList;
    },
    createColorPickers() {
      if (!this.palette.default) {
        for (let i = 0; i < this.palette.colors.length; i++) {
          const pickr = Pickr.create({
            el: `#color-picker-${i}`,
            theme: 'classic',
            showAlways: true,
            inline: true,
            lockOpacity: true,
            comparison: false,
            default: `hsv(${this.palette.colors[i][0] * 360}, ${this.palette.colors[i][1] * 100}%, ${this.palette.colors[i][2] * 100}%)`,
            swatches: null,
            components: {
              preview: false,
              opacity: false,
              hue: true,
              interaction: { hex: true, rgba: true, hsla: true, hsva: true, input: true },
            },
          });
          pickr.index = i;
          pickr.on('changestop', (c, instance) => {
            const color = instance.getColor();
            this.palette.colors[instance.index] = [
              color.h / 360, color.s / 100, color.v / 100
            ];
            this.updatePaletteContents();
          });
        }
      }
    }
  },
  mounted() {
    this.$nextTick(this.createCodeEditor);
    this.$nextTick(this.createColorPickers);
  },
  template: `
    <div class="group-controls">
      <!-- Basic Settings -->
      <div class="control-section">
        <h4 class="section-title">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="3"></circle>
            <path d="M12 1v6m0 6v6"></path>
          </svg>
          Basic Settings
        </h4>
        <slider-number-input
          v-bind:path="'groups.' + name + '.brightness'"
          label="Brightness"
          unit=""
          v-bind:min="0"
          v-bind:max="1"
          v-bind:step="0.01"
        ></slider-number-input>
        <slider-number-input
          v-bind:path="'groups.' + name + '.saturation'"
          label="Saturation"
          unit=""
          v-bind:min="0"
          v-bind:max="1"
          v-bind:step="0.01"
        ></slider-number-input>
      </div>

      <!-- Pattern Configuration -->
      <div class="control-section">
        <h4 class="section-title">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M12 2L2 7l10 5 10-5-10-5z"></path>
            <path d="M2 17l10 5 10-5M2 12l10 5 10-5"></path>
          </svg>
          Pattern
        </h4>
        <div class="input-group">
          <label class="input-label">Animation Pattern</label>
          <select
            class="select-modern"
            autocomplete="off"
            v-model="functionKey"
            @change="updateFunction"
          >
            <option
              v-for="(f, id) in functions"
              v-bind:value="id"
            >
              {{ f.name }}
            </option>
          </select>
        </div>
        
        <slider-number-input
          v-bind:path="'groups.' + name + '.speed'"
          label="Animation Speed"
          unit="Hz"
          v-bind:min="0"
          v-bind:max="2"
          v-bind:step="0.01"
        ></slider-number-input>
        
        <slider-number-input
          v-bind:path="'groups.' + name + '.scale'"
          label="Pattern Scale"
          unit=""
          v-bind:min="-10"
          v-bind:max="10"
          v-bind:step="0.01"
        ></slider-number-input>

        <!-- Pattern Management -->
        <div class="pattern-management">
          <div class="input-group">
            <label class="input-label">Pattern Name</label>
            <div class="input-with-buttons">
              <input
                type="text"
                class="input-modern"
                v-model="animFunction.name"
                @change="updateFunctionSource"
                v-bind:disabled="animFunction.default"
                autocomplete="off"
                placeholder="Pattern name"
              >
              <div class="button-group">
                <button
                  class="btn btn-secondary btn-sm"
                  @click="newFunction"
                  title="Create a copy of this pattern"
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                    <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                  </svg>
                  New
                </button>
                <button
                  class="btn btn-danger btn-sm"
                  v-show="!animFunction.default"
                  @click="deleteFunction"
                  title="Delete this pattern"
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polyline points="3 6 5 6 21 6"></polyline>
                    <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6"></path>
                  </svg>
                  Delete
                </button>
              </div>
            </div>
          </div>

          <!-- Compile Status -->
          <div class="compile-section">
            <div class="compile-status" v-bind:class="sourceStatusClass">
              <svg v-if="sourceStatusClass === 'status-success'" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
                <polyline points="22 4 12 14.01 9 11.01"></polyline>
              </svg>
              <svg v-else-if="sourceStatusClass === 'status-error'" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="10"></circle>
                <line x1="12" y1="8" x2="12" y2="12"></line>
                <line x1="12" y1="16" x2="12.01" y2="16"></line>
              </svg>
              <svg v-else width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="10"></circle>
                <line x1="12" y1="16" x2="12" y2="12"></line>
                <line x1="12" y1="8" x2="12.01" y2="8"></line>
              </svg>
              <span>{{ sourceStatus }}</span>
            </div>
            <button
              class="btn btn-primary btn-sm"
              @click="compileFunction"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="16 18 22 12 16 6"></polyline>
                <polyline points="8 6 2 12 8 18"></polyline>
              </svg>
              Compile
            </button>
          </div>
        </div>

        <!-- Code Editor -->
        <div class="code-editor-wrapper">
          <div ref="code" :key="functionKey"></div>
        </div>
      </div>

      <!-- Color Palette Configuration -->
      <div class="control-section">
        <h4 class="section-title">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="13.5" cy="6.5" r=".5"></circle>
            <circle cx="17.5" cy="10.5" r=".5"></circle>
            <circle cx="8.5" cy="7.5" r=".5"></circle>
            <circle cx="6.5" cy="12.5" r=".5"></circle>
            <path d="M12 2C6.5 2 2 6.5 2 12s4.5 10 10 10c.926 0 1.648-.746 1.648-1.688 0-.437-.18-.835-.437-1.125-.29-.289-.438-.652-.438-1.125a1.64 1.64 0 0 1 1.668-1.668h1.996c3.051 0 5.555-2.503 5.555-5.554C21.965 6.012 17.461 2 12 2z"></path>
          </svg>
          Color Palette
        </h4>
        
        <div class="input-group">
          <label class="input-label">Select Palette</label>
          <div class="palette-selector">
            <select
              class="select-modern"
              autocomplete="off"
              v-model="paletteKey"
              @change="updatePalette"
            >
              <option
                v-for="(p, id) in palettes"
                v-bind:value="id"
              >
                {{ p.name }}
              </option>
            </select>
            <button
              class="btn btn-secondary btn-sm"
              @click="togglePaletteList"
              v-bind:class="{'active': showPaletteList}"
              title="Show all palettes"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="8" y1="6" x2="21" y2="6"></line>
                <line x1="8" y1="12" x2="21" y2="12"></line>
                <line x1="8" y1="18" x2="21" y2="18"></line>
                <line x1="3" y1="6" x2="3.01" y2="6"></line>
                <line x1="3" y1="12" x2="3.01" y2="12"></line>
                <line x1="3" y1="18" x2="3.01" y2="18"></line>
              </svg>
              {{ showPaletteList ? 'Hide' : 'Show' }} All
            </button>
          </div>
        </div>

        <!-- Palette Preview -->
        <palette-color-bar
          v-bind:colors="palette.colors"
          v-if="!showPaletteList"
          :key="palettePreviewKey"
          class="palette-preview">
        </palette-color-bar>

        <!-- Palette List -->
        <div class="palette-list-wrapper" v-if="showPaletteList">
          <div class="palette-list-item" v-for="(p, id) in palettes" @click="selectPalette(id)" :class="{'active': id == paletteKey}">
            <div class="palette-list-name">{{ p.name }}</div>
            <palette-color-bar v-bind:colors="p.colors" :key="palettePreviewKey"></palette-color-bar>
          </div>
        </div>

        <!-- Palette Management -->
        <div class="palette-management">
          <div class="input-group">
            <label class="input-label">Palette Name</label>
            <div class="input-with-buttons">
              <input
                type="text"
                class="input-modern"
                v-model="palette.name"
                @change="updatePaletteContents"
                v-bind:disabled="palette.default"
                autocomplete="off"
                placeholder="Palette name"
              >
              <div class="button-group">
                <button
                  class="btn btn-secondary btn-sm"
                  @click="newPalette"
                  title="Create a copy of this palette"
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                    <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                  </svg>
                  New
                </button>
                <button
                  class="btn btn-danger btn-sm"
                  v-show="!palette.default"
                  @click="deletePalette"
                  title="Delete this palette"
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polyline points="3 6 5 6 21 6"></polyline>
                    <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6"></path>
                  </svg>
                  Delete
                </button>
              </div>
            </div>
          </div>

          <!-- Color Pickers -->
          <div class="color-picker-section" v-if="!palette.default">
            <div
              v-for="(color, i) in palette.colors"
              :key="paletteKey + '.' + palette.colors.length + '.' + i"
              class="color-picker-item"
            >
              <div class="color-picker-header">
                <span class="color-picker-label">Color {{ i + 1 }}</span>
                <div class="color-picker-actions">
                  <button
                    class="btn-icon"
                    @click="addColor(i)"
                    title="Add color after this"
                  >
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <line x1="12" y1="5" x2="12" y2="19"></line>
                      <line x1="5" y1="12" x2="19" y2="12"></line>
                    </svg>
                  </button>
                  <button
                    class="btn-icon btn-icon-danger"
                    @click="deleteColor(i)"
                    title="Remove this color"
                    v-bind:disabled="palette.colors.length <= 2"
                  >
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <line x1="5" y1="12" x2="19" y2="12"></line>
                    </svg>
                  </button>
                </div>
              </div>
              <div class="color-picker" v-bind:id="'color-picker-' + i"></div>
            </div>
          </div>
        </div>
      </div>
    </div>
  `,
};
