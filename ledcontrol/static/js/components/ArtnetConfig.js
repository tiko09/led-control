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
          artnet_channel_offset: 0
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