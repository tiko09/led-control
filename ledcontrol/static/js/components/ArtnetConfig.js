export default {
    name: 'ArtnetConfig',
    template: `
      <div class="card">
        <h3>ArtNet</h3>
        <div v-if="loading">Lade...</div>
        <div v-else>
          <label style="display:flex;align-items:center;gap:.5rem;">
            <input type="checkbox" v-model="form.enable_artnet">
            <span>ArtNet Modus aktivieren</span>
          </label>
  
          <div class="grid" style="margin-top:0.75rem;gap:0.75rem;"
               :style="{opacity: form.enable_artnet ? 1 : 0.5}">
            <label>
              <span>Universe</span>
              <input type="number" min="0" max="32767" v-model.number="form.artnet_universe">
            </label>
            <label>
              <span>Channel Offset</span>
              <input type="number" min="0" max="511" v-model.number="form.artnet_channel_offset">
            </label>
            <label>
              <span>LEDs pro Pixel</span>
              <input type="number" min="1" max="1024" v-model.number="form.artnet_group_size">
            </label>
            <label>
              <span>Smoothing-Filter</span>
              <select v-model="form.artnet_smoothing">
                <option value="none">Keiner</option>
                <option value="average">Gleitender Mittelwert</option>
                <option value="lerp">Sanft (Lerp)</option>
              </select>
            </label>
            <label>
              <span>Filtergröße</span>
              <input type="number" min="1" max="20" v-model.number="form.artnet_filter_size">
            </label>
            <label>
              <span>Frame Interpolation</span>
              <select v-model="form.artnet_frame_interpolation">
                <option value="none">None</option>
                <option value="average">Moving Average</option>
                <option value="lerp">Lerp</option>
              </select>
            </label>
            <label>
              <span>Interpolation Size</span>
              <input type="number" min="1" max="20" v-model.number="form.artnet_frame_interp_size">
            </label>
            <p style="grid-column:1/-1;font-size:.75rem;color:#888;margin:0;">
              Effektive phys. Kapazität: {{
                Math.floor((512 - form.artnet_channel_offset)/4) * form.artnet_group_size
              }} LEDs (aktueller Strip gesteuert durch {{
                Math.ceil( form.artnet_group_size>0 ? (form.artnet_group_size) : 1 )
              }}er-Gruppen)
            </p>
          </div>
  
          <div style="margin-top:1rem;display:flex;gap:.5rem;">
            <button @click="save" :disabled="saving">{{ saving ? 'Speichere...' : 'Speichern' }}</button>
            <button @click="load" :disabled="saving">Neu laden</button>
            <span v-if="message" :style="{color: messageType==='error'?'#f55':'#5c5'}">{{ message }}</span>
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
          artnet_smoothing: "none",
          artnet_filter_size: 2,
          artnet_frame_interpolation: "none",
          artnet_frame_interp_size: 2
        }
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
          this.form.artnet_filter_size = j.artnet_filter_size ?? 2;
          this.form.artnet_frame_interpolation = j.artnet_frame_interpolation ?? "none";
          this.form.artnet_frame_interp_size = j.artnet_frame_interp_size ?? 2;
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
      }
    },
    mounted() {
      this.load();
    }
  };