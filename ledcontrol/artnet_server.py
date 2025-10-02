# artnet_server.py
import socket
import struct
import threading
import logging
from queue import Queue, Empty
from typing import Callable, Optional

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
        self.log.debug("Selfe poll")
        applied = 0
        while True:
            try:
                universe, data = self._queue.get_nowait()
            except Empty:
                break
            if universe != self.universe:
                self.log.debug("Ignoriere Paket für anderes Universe (%d != %d)",
                               universe, self.universe)
                continue
            leds = self._apply_dmx(data)
            self.log.debug("ArtNet Paket angewandt: universe=%d bytes=%d leds_updated=%d",
                           universe, len(data), leds)
            applied += 1
        return applied

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
                # Sequence Byte
                seq = pkt[12]
                universe = struct.unpack_from("<H", pkt, 14)[0]
                length = struct.unpack_from(">H", pkt, 16)[0]
                data = pkt[18:18+length]
            except struct.error:
                continue
            self.log.debug("Empfangen ArtDMX von %s universe=%d seq=%d length=%d",
                           addr, universe, seq, length)
            self._queue.put((universe, data))

    def _apply_dmx(self, data: bytes) -> int:
        updated = 0
        cpl = self.channels_per_led
        if self.log.isEnabledFor(logging.DEBUG):
            per_led_lines = []
            channel_pairs = []  # kompakte Liste kanal=wert
        for led_index in range(self.led_count):
            base = self.channel_offset + led_index * cpl
            if base >= len(data):
                break

            # Einlesen (fehlende = 0)
            r = data[base] if base < len(data) else 0
            g = data[base + 1] if base + 1 < len(data) else 0
            b = data[base + 2] if base + 2 < len(data) else 0
            w = data[base + 3] if cpl >= 4 and base + 3 < len(data) else 0

            self.set_led_rgbw(led_index, r, g, b, w)
            updated += 1

            if self.log.isEnabledFor(logging.DEBUG):
                # DMX Kanäle 1-basiert ausgeben
                ch_r = base + 1
                ch_g = base + 2
                ch_b = base + 3
                ch_w = base + 4
                if cpl >= 4:
                    per_led_lines.append(
                        f"LED{led_index}: R(ch{ch_r})={r} G(ch{ch_g})={g} B(ch{ch_b})={b} W(ch{ch_w})={w}"
                    )
                    channel_pairs.extend((
                        f"{ch_r}={r}", f"{ch_g}={g}", f"{ch_b}={b}", f"{ch_w}={w}"
                    ))
                else:
                    per_led_lines.append(
                        f"LED{led_index}: R(ch{ch_r})={r} G(ch{ch_g})={g} B(ch{ch_b})={b}"
                    )
                    channel_pairs.extend((
                        f"{ch_r}={r}", f"{ch_g}={g}", f"{ch_b}={b}"
                    ))

        if self.log.isEnabledFor(logging.DEBUG) and updated:
            # Detailliert pro LED
            for line in per_led_lines:
                self.log.debug(line)
            # Kompakte Zeile
            self.log.debug("DMX Werte kompakt: %s", ", ".join(channel_pairs))
        return updated