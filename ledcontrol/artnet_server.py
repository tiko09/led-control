# artnet_server.py
import socket
import struct
import threading
import logging
from queue import Queue, Empty
from typing import Callable, Optional
import time  # (oben ergänzen)

ARTNET_PORT = 6454
ARTNET_HEADER = b'Art-Net\x00'
OPCODE_ART_DMX = 0x5000  # little endian in packet

class ArtNetServer:
    def __init__(self, set_led_rgbw, led_count: int,
                 universe: int = 0, channel_offset: int = 0,
                 channels_per_led: int = 4, group_size: int = 1,
                 frame_interpolation: str = "none", frame_interp_size: int = 2, host: str = "0.0.0.0"):
        self.set_led_rgbw = set_led_rgbw
        self.led_count = led_count
        self.universe = universe
        self.channel_offset = channel_offset
        self.channels_per_led = channels_per_led
        self.group_size = max(1, group_size)
        self.frame_interpolation = frame_interpolation
        self.frame_interp_size = max(1, frame_interp_size)
        self.host = host
        self._last_values = [ [] for _ in range(led_count) ]  # Liste von Listen für Filter
        self._sock: Optional[socket.socket] = None
        self._thread: Optional[threading.Thread] = None
        self._running = threading.Event()
        self._queue: Queue = Queue()
        self.log = logging.getLogger("artnet")
        self._fps_start = time.time()
        self._fps_last_report = self._fps_start
        self._fps_count = 0
        self._fps_report_interval = 10.0  # Sekunden

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

    def poll(self):
        # Keine Funktion mehr nötig bei Direktverarbeitung – nur für Rückwärtskompatibilität
        return 0

    def _run(self):
        while self._running.is_set():
            try:
                pkt, addr = self._sock.recvfrom(2048)
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
        if expanded:
            self.set_led_rgbw(expanded, 0)

        # FPS
        self._fps_count += 1
        now = time.time()
        if (now - self._fps_last_report) >= self._fps_report_interval:
            total_elapsed = now - self._fps_start
            avg_fps_total = self._fps_count / total_elapsed if total_elapsed > 0 else 0.0
            self.log.info("ArtNet FPS: frames=%d time=%.1fs avg=%.2f",
                          self._fps_count, total_elapsed, avg_fps_total)
            self._fps_last_report = now
            self._fps_start = now
            self._fps_count = 0
        return phys_used