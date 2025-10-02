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
                 channels_per_led: int = 4, host: str = "0.0.0.0"):
        self.set_led_rgbw = set_led_rgbw
        self.led_count = led_count
        self.universe = universe
        self.channel_offset = channel_offset
        self.channels_per_led = channels_per_led
        self.host = host
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
        self.set_led_rgbw(data,0)

                # FPS-Messung
        self._fps_count += 1
        now = time.time()
        elapsed = now - self._fps_last_report
        if elapsed >= self._fps_report_interval:
            total_elapsed = now - self._fps_start
            avg_fps_total = self._fps_count / total_elapsed if total_elapsed > 0 else 0.0
            interval_fps = self._fps_count / total_elapsed if total_elapsed > 0 else 0.0  # alternativ: (self._fps_count_interval/elapsed)
            self.log.info(
                "ArtNet FPS: total_frames=%d total_time=%.1fs avg_fps=%.2f (Intervall %.0fs)",
                self._fps_count, total_elapsed, avg_fps_total, self._fps_report_interval
            )
            self._fps_last_report = now
            # Optional: Für gleitenden Durchschnitt statt total neu starten:
            # self._fps_start = now
            # self._fps_count = 0
        return (len(data) // self.channels_per_led)