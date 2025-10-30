// led-control WS2812B LED Controller Server
// LED Visualizer Page - Real-time LED strip visualization

export default {
  name: 'VisualizerPage',
  data() {
    return {
      socket: null,
      connected: false,
      ledCount: 0,
      targetFps: 30,
      currentFps: 0,
      pixels: [],
      showBlur: true,
      showStats: true,
      framesReceived: 0,
      lastFrameTime: 0,
      canvas: null,
      ctx: null,
    }
  },
  computed: {
    ledSize() {
      return 20;
    },
    ledGap() {
      return 4;
    }
  },
  methods: {
    connect() {
      // Connect to visualizer WebSocket namespace
      this.socket = io('/visualizer', {
        transports: ['websocket', 'polling']
      });

      this.socket.on('connect', () => {
        this.connected = true;
      });

      this.socket.on('disconnect', () => {
        this.connected = false;
      });

      this.socket.on('connected', (data) => {
        this.ledCount = data.led_count;
        this.targetFps = data.fps;
        this.$nextTick(() => {
          this.initCanvas();
        });
      });

      this.socket.on('led_frame', (data) => {
        this.handleFrame(data);
      });
    },

    disconnect() {
      if (this.socket) {
        this.socket.close();
        this.socket = null;
      }
      this.connected = false;
    },

    initCanvas() {
      this.canvas = this.$refs.ledCanvas;
      if (!this.canvas) return;

      this.ctx = this.canvas.getContext('2d', { alpha: false });
      
      // Set canvas size based on LED count and scale
      const totalWidth = (this.ledSize + this.ledGap) * this.ledCount;
      this.canvas.width = totalWidth;
      this.canvas.height = this.ledSize + 20;

      // Clear canvas
      this.ctx.fillStyle = '#0a0b0d';
      this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
    },

    handleFrame(data) {
      if (!this.ctx || !data.pixels) return;

      const now = performance.now();
      if (this.lastFrameTime > 0) {
        const delta = now - this.lastFrameTime;
        this.currentFps = Math.round(1000 / delta);
      }
      this.lastFrameTime = now;
      this.framesReceived++;

      // Parse pixel data (flat RGB array)
      this.pixels = [];
      for (let i = 0; i < data.pixels.length; i += 3) {
        this.pixels.push({
          r: data.pixels[i],
          g: data.pixels[i + 1],
          b: data.pixels[i + 2]
        });
      }

      this.drawLEDs();
    },

    drawLEDs() {
      if (!this.ctx || this.pixels.length === 0) return;

      // Clear canvas
      this.ctx.fillStyle = '#0a0b0d';
      this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);

      // Draw each LED
      for (let i = 0; i < this.pixels.length; i++) {
        const pixel = this.pixels[i];
        const x = i * (this.ledSize + this.ledGap) + this.ledGap;
        const y = 10;

        // Draw LED with glow effect
        if (this.showBlur) {
          // Outer glow
          const gradient = this.ctx.createRadialGradient(
            x + this.ledSize / 2, y + this.ledSize / 2, 0,
            x + this.ledSize / 2, y + this.ledSize / 2, this.ledSize * 1.5
          );
          gradient.addColorStop(0, `rgba(${pixel.r}, ${pixel.g}, ${pixel.b}, 0.8)`);
          gradient.addColorStop(0.5, `rgba(${pixel.r}, ${pixel.g}, ${pixel.b}, 0.3)`);
          gradient.addColorStop(1, `rgba(${pixel.r}, ${pixel.g}, ${pixel.b}, 0)`);
          
          this.ctx.fillStyle = gradient;
          this.ctx.fillRect(
            x - this.ledSize * 0.5,
            y - this.ledSize * 0.5,
            this.ledSize * 2.5,
            this.ledSize * 2.5
          );
        }

        // Core LED
        this.ctx.fillStyle = `rgb(${pixel.r}, ${pixel.g}, ${pixel.b})`;
        this.ctx.beginPath();
        this.ctx.arc(
          x + this.ledSize / 2,
          y + this.ledSize / 2,
          this.ledSize / 2,
          0,
          Math.PI * 2
        );
        this.ctx.fill();
      }
    },

    toggleBlur() {
      this.drawLEDs();
    }
  },

  mounted() {
    this.connect();
  },

  beforeUnmount() {
    this.disconnect();
  },

  template: `
    <div class="page visualizer-page">
      <!-- Header Card -->
      <div class="card">
        <div class="card-header">
          <div class="card-header-left">
            <svg class="card-icon" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="2" y="3" width="20" height="14" rx="2" ry="2"></rect>
              <line x1="8" y1="21" x2="16" y2="21"></line>
              <line x1="12" y1="17" x2="12" y2="21"></line>
            </svg>
            <h2 class="card-title">LED Visualizer</h2>
            <span class="card-badge" :class="{ 'badge-success': connected, 'badge-error': !connected }">
              {{ connected ? 'Connected' : 'Disconnected' }}
            </span>
          </div>
        </div>
        <div class="card-body">
          <!-- Controls -->
          <div class="visualizer-controls">
            <div class="control-group">
              <label class="toggle-label">
                <input 
                  type="checkbox" 
                  class="toggle-input" 
                  v-model="showBlur" 
                  @change="toggleBlur"
                >
                <span class="toggle-slider"></span>
                <span class="toggle-text">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <circle cx="12" cy="12" r="10"></circle>
                    <circle cx="12" cy="12" r="6"></circle>
                    <circle cx="12" cy="12" r="2"></circle>
                  </svg>
                  Diffusion Effect (Milky Glass)
                </span>
              </label>
            </div>

            <div class="control-group">
              <label class="toggle-label">
                <input type="checkbox" class="toggle-input" v-model="showStats">
                <span class="toggle-slider"></span>
                <span class="toggle-text">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <line x1="18" y1="20" x2="18" y2="10"></line>
                    <line x1="12" y1="20" x2="12" y2="4"></line>
                    <line x1="6" y1="20" x2="6" y2="14"></line>
                  </svg>
                  Show Statistics
                </span>
              </label>
            </div>
          </div>

          <!-- Stats -->
          <div v-if="showStats" class="visualizer-stats">
            <div class="stat-item">
              <div class="stat-label">LEDs</div>
              <div class="stat-value">{{ ledCount }}</div>
            </div>
            <div class="stat-item">
              <div class="stat-label">Target FPS</div>
              <div class="stat-value">{{ targetFps }}</div>
            </div>
            <div class="stat-item">
              <div class="stat-label">Current FPS</div>
              <div class="stat-value">{{ currentFps }}</div>
            </div>
            <div class="stat-item">
              <div class="stat-label">Frames</div>
              <div class="stat-value">{{ framesReceived }}</div>
            </div>
          </div>
        </div>
      </div>

      <!-- LED Canvas -->
      <div class="card visualizer-canvas-container">
        <div class="canvas-wrapper" :class="{ 'blur-enabled': showBlur }">
          <canvas ref="ledCanvas" class="led-canvas"></canvas>
          <div v-if="showBlur" class="milky-glass-overlay"></div>
        </div>
        <div v-if="!connected" class="no-connection">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="1" y1="1" x2="23" y2="23"></line>
            <path d="M16.72 11.06A10.94 10.94 0 0 1 19 12.55"></path>
            <path d="M5 12.55a10.94 10.94 0 0 1 5.17-2.39"></path>
            <path d="M10.71 5.05A16 16 0 0 1 22.58 9"></path>
            <path d="M1.42 9a15.91 15.91 0 0 1 4.7-2.88"></path>
            <path d="M8.53 16.11a6 6 0 0 1 6.95 0"></path>
            <line x1="12" y1="20" x2="12.01" y2="20"></line>
          </svg>
          <p>Not connected to LED controller</p>
        </div>
      </div>
    </div>
  `
};
