# artnet_server.py
import socket
import struct
import threading
import logging
import math
from typing import Callable, Optional
import time

# Try to import C extension for high-performance spatial smoothing
try:
    from ledcontrol import _ledcontrol_artnet_utils as c_artnet
    HAS_C_ARTNET = True
    print("Using C extension for ArtNet spatial smoothing (high performance)")
except ImportError:
    HAS_C_ARTNET = False
    print("C extension not available for ArtNet, using Python fallback")

ARTNET_PORT = 6454
ARTNET_HEADER = b'Art-Net\x00'
OPCODE_ART_DMX = 0x5000  # little endian in packet

class ArtNetServer:
    def __init__(self, set_led_rgbw, led_count: int,
                 universe: int = 0, channel_offset: int = 0,
                 channels_per_led: int = 4, group_size: int = 1,
                 frame_interpolation: str = "none", frame_interp_size: int = 2,
                 spatial_smoothing: str = "none", spatial_size: int = 1,
                 host: str = "0.0.0.0"):
        self.set_led_rgbw = set_led_rgbw
        self.led_count = led_count
        self.universe = universe
        self.channel_offset = channel_offset
        self.channels_per_led = channels_per_led
        self.group_size = max(1, group_size)
        self.frame_interpolation = frame_interpolation
        self.frame_interp_size = max(1, frame_interp_size)
        self.host = host
        self.spatial_smoothing = spatial_smoothing
        self.spatial_size = max(1, spatial_size)
        self._last_values = [ [] for _ in range(led_count) ]  # Liste von Listen für Filter
        self._sock: Optional[socket.socket] = None
        self._thread: Optional[threading.Thread] = None
        self._running = threading.Event()
        self.log = logging.getLogger("artnet")
        self._fps_start = time.time()
        self._fps_last_report = self._fps_start
        self._fps_count = 0
        self._fps_report_interval = 10.0  # Sekunden
        # Timing debug
        self._last_packet_time = None
        self._packet_intervals = []
        self._debug_interval_report = 5.0  # Report every 5 seconds
        self._debug_last_report = time.time()

    def start(self):
        if self._thread and self._thread.is_alive():
            self.log.debug("ArtNetServer bereits aktiv")
            return
        self._running.set()
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind((self.host, ARTNET_PORT))
        self._thread = threading.Thread(target=self._run,
                                        name="ArtNetServer",
                                        daemon=True)
        self._thread.start()
        self.log.info("ArtNet Server gestartet (Universe=%d Offset=%d LEDs=%d)",
                      self.universe, self.channel_offset, self.led_count)

    def stop(self):
        self._running.clear()
        if self._sock:
            try:
                self._sock.close()
            except OSError:
                pass
        if self._thread:
            self._thread.join(timeout=1)
        self.log.info("ArtNet Server gestoppt")

    def _run(self):
        self.log.info("ArtNet receiver thread started, waiting for packets...")
        packet_count = 0
        while self._running.is_set():
            try:
                pkt, addr = self._sock.recvfrom(2048)
                packet_count += 1
                
                # Measure time between packets
                now = time.time()
                if self._last_packet_time is not None:
                    interval = now - self._last_packet_time
                    self._packet_intervals.append(interval)
                    
                    # Log every 100th packet immediately
                    if packet_count % 100 == 0:
                        self.log.info("📦 Received packet #%d, interval: %.3fms", packet_count, interval * 1000)
                        
                self._last_packet_time = now
                
            except OSError:
                if not self._running.is_set():
                    break
                continue

            if not pkt.startswith(ARTNET_HEADER):
                continue
            if len(pkt) < 18:
                continue
            try:
                op_code = struct.unpack_from("<H", pkt, 8)[0]
                if op_code != OPCODE_ART_DMX:
                    continue
                seq = pkt[12]                  # Sequence (optional Nutzung)
                universe = struct.unpack_from("<H", pkt, 14)[0]
                length = struct.unpack_from(">H", pkt, 16)[0]
                data = pkt[18:18+length]
            except struct.error:
                continue

            if universe != self.universe:
                self.log.debug("Ignoriere Paket anderes Universe (%d != %d)", universe, self.universe)
                continue

            leds = self._apply_dmx(data)
            self.log.debug(
                "ArtNet Direkt angewandt: from=%s universe=%d seq=%d bytes=%d leds_updated=%d",
                addr, universe, seq, len(data), leds
            )
            
            # Report packet timing statistics periodically
            now = time.time()
            if (now - self._debug_last_report) >= self._debug_interval_report:
                if self._packet_intervals:
                    avg_interval = sum(self._packet_intervals) / len(self._packet_intervals)
                    min_interval = min(self._packet_intervals)
                    max_interval = max(self._packet_intervals)
                    estimated_fps = 1.0 / avg_interval if avg_interval > 0 else 0
                    self.log.info("📊 Packet Timing: count=%d avg=%.3fms (%.1f FPS) min=%.3fms max=%.3fms",
                                 len(self._packet_intervals),
                                 avg_interval * 1000,
                                 estimated_fps,
                                 min_interval * 1000,
                                 max_interval * 1000)
                    self._packet_intervals = []
                self._debug_last_report = now

    def _apply_dmx(self, data: bytes) -> int:
        group = self.group_size
        cpl = self.channels_per_led
        offset = self.channel_offset
        frame_interpolation = self.frame_interpolation
        frame_interp_size = self.frame_interp_size
        usable = len(data) - offset
        dmx_pixels = usable // cpl
        phys_used = 0
        expanded = bytearray()
        for dmx_i in range(dmx_pixels):
            if phys_used >= self.led_count:
                break
            base = offset + dmx_i * cpl
            r = data[base] if base < len(data) else 0
            g = data[base+1] if base+1 < len(data) else 0
            b = data[base+2] if base+2 < len(data) else 0
            w = data[base+3] if cpl >= 4 and base+3 < len(data) else 0
            for _ in range(group):
                if phys_used >= self.led_count:
                    break
                idx = phys_used
                # --- Smoothing mit Filtergröße ---
                history = self._last_values[idx]
                history.append((r, g, b, w))
                if len(history) > frame_interp_size:
                    history.pop(0)
                if frame_interpolation == "average" and len(history) > 1:
                    r_s = sum(x[0] for x in history) // len(history)
                    g_s = sum(x[1] for x in history) // len(history)
                    b_s = sum(x[2] for x in history) // len(history)
                    w_s = sum(x[3] for x in history) // len(history)
                    r, g, b, w = r_s, g_s, b_s, w_s
                elif frame_interpolation == "lerp" and len(history) > 1:
                    alpha = 1.0 / frame_interp_size
                    prev = history[-2]
                    r = int(prev[0] + alpha * (r - prev[0]))
                    g = int(prev[1] + alpha * (g - prev[1]))
                    b = int(prev[2] + alpha * (b - prev[2]))
                    w = int(prev[3] + alpha * (w - prev[3]))
                self._last_values[idx] = history
                expanded.extend((r, g, b, w))
                phys_used += 1
        if expanded and self.spatial_smoothing == "none":
            # Directly update LEDs when packet arrives
            self.set_led_rgbw(expanded, 0)

        # --- Spatial Smoothing über Nachbar-LEDs ---
        if self.spatial_smoothing != "none" and self.spatial_size > 1:
            n_leds = phys_used
            window = self.spatial_size
            
            if HAS_C_ARTNET:
                # Use high-performance C extension
                smoothing_type_map = {
                    "average": 0,
                    "lerp": 1,
                    "gaussian": 2
                }
                smoothing_type = smoothing_type_map.get(self.spatial_smoothing, 0)
                
                # Allocate output buffer
                smoothed = bytearray(n_leds * 4)
                
                # Call C function
                c_artnet.spatial_smooth_rgbw_py(
                    bytes(expanded), smoothed,
                    n_leds, window, smoothing_type
                )
                
                expanded = smoothed
            else:
                # Python fallback
                cpl = self.channels_per_led
                #check if window is uneven if not expand by one
                if window % 2 == 0:
                    window += 1
                half = window // 2
                smoothed = bytearray()
                
                # build filter Kernel based on specified window size and filter function
                if self.spatial_smoothing == "average":
                    kernel = [1.0 / window] * window
                elif self.spatial_smoothing == "lerp":
                    center = window // 2
                    raw_kernel = [window - abs(i - center) for i in range(window)]
                    kernel_sum = sum(raw_kernel)
                    kernel = [k / kernel_sum for k in raw_kernel]
                elif self.spatial_smoothing == "gaussian":
                    # Gauß-Kernel berechnen (sigma proportional zu window)
                    center = window // 2
                    sigma = max(1.0, window / 4.0)
                    kernel = [math.exp(-0.5 * ((i - center) / sigma) ** 2) for i in range(window)]
                    kernel_sum = sum(kernel)
                    kernel = [k / kernel_sum for k in kernel]
                else:
                    kernel = [1.0 / window] * window  # fallback

                # print the kernel
                self.log.debug("Spatial Smoothing Kernel: %s", kernel)

                #itterate of all leds
                for i in range(n_leds):
                    acc = [0, 0, 0, 0]
                    # apply kernel
                    for k in range(len(kernel)):
                        neighbor_idx = i + (k - half)
                        if 0 <= neighbor_idx < n_leds:
                            base = neighbor_idx * cpl
                            r = expanded[base]
                            g = expanded[base + 1]
                            b = expanded[base + 2]
                            w = expanded[base + 3] if cpl == 4 else 0
                            weight = kernel[k]
                            acc[0] += r * weight
                            acc[1] += g * weight
                            acc[2] += b * weight
                            acc[3] += w * weight
                    smoothed.extend((int(acc[0]), int(acc[1]), int(acc[2]), int(acc[3])))
                    
                expanded = smoothed
            
            if expanded:
                # Directly update LEDs when packet arrives  
                self.set_led_rgbw(expanded, 0)

        # FPS
        self._fps_count += 1
        now = time.time()
        
        # Debug: Report packet timing statistics every 5 seconds
        if (now - self._debug_last_report) >= self._debug_interval_report:
            if self._packet_intervals:
                avg_interval = sum(self._packet_intervals) / len(self._packet_intervals)
                min_interval = min(self._packet_intervals)
                max_interval = max(self._packet_intervals)
                estimated_fps = 1.0 / avg_interval if avg_interval > 0 else 0
                self.log.info("📊 Packet Timing: count=%d avg=%.3fms (%.1f FPS) min=%.3fms max=%.3fms",
                             len(self._packet_intervals),
                             avg_interval * 1000,
                             estimated_fps,
                             min_interval * 1000,
                             max_interval * 1000)
                self._packet_intervals = []
            self._debug_last_report = now
        
        if (now - self._fps_last_report) >= self._fps_report_interval:
            total_elapsed = now - self._fps_start
            avg_fps_total = self._fps_count / total_elapsed if total_elapsed > 0 else 0.0
            self.log.info("ArtNet FPS: frames=%d time=%.1fs avg=%.2f",
                          self._fps_count, total_elapsed, avg_fps_total)
            self._fps_last_report = now
            self._fps_start = now
            self._fps_count = 0
        return phys_used