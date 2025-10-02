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
    def __init__(
        self,
        set_led_rgb: Callable[[int, int, int, int], None],
        led_count: int,
        universe: int = 0,
        channel_offset: int = 0,
        host: str = "0.0.0.0",
    ):
        self.set_led_rgb = set_led_rgb
        self.led_count = led_count
        self.universe = universe
        self.channel_offset = channel_offset
        self.host = host
        self._sock: Optional[socket.socket] = None
        self._thread: Optional[threading.Thread] = None
        self._running = threading.Event()
        self._queue: Queue = Queue()
        self.log = logging.getLogger("artnet")

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._running.set()
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind((self.host, ARTNET_PORT))
        self._thread = threading.Thread(target=self._run, name="ArtNetServer", daemon=True)
        self._thread.start()
        self.log.info("ArtNet Server gestartet (Universe=%d Offset=%d)", self.universe, self.channel_offset)

    def stop(self):
        self._running.clear()
        if self._sock:
            try:
                self._sock.close()
            except OSError:
                pass
        if self._thread:
            self._thread.join(timeout=1)

    def poll(self):
        """Vom Haupt-Thread regelmäßig aufrufen um Queue-Einträge anzuwenden."""
        applied = 0
        while True:
            try:
                universe, data = self._queue.get_nowait()
            except Empty:
                break
            if universe != self.universe:
                continue
            self._apply_dmx(data)
            applied += 1
        return applied

    def _run(self):
        while self._running.is_set():
            try:
                pkt, _addr = self._sock.recvfrom(1024)
            except OSError:
                if not self._running.is_set():
                    break
                continue
            if not pkt.startswith(ARTNET_HEADER):
                continue
            if len(pkt) < 18:
                continue
            # Header (8) + OpCode(2 LE) + ProtVer(2) + Seq(1) + Phys(1) + Universe(2 LE) + Length(2 BE) + Data
            try:
                op_code = struct.unpack_from("<H", pkt, 8)[0]
                if op_code != OPCODE_ART_DMX:
                    continue
                universe = struct.unpack_from("<H", pkt, 14)[0]
                length = struct.unpack_from(">H", pkt, 16)[0]
                data = pkt[18:18+length]
            except struct.error:
                continue
            self._queue.put((universe, data))

    def _apply_dmx(self, data: bytes):
        # DMX Kanäle 1-basiert, unsere Array-Indices 0-basiert
        # channel_offset lässt Überspringen erster Kanäle zu
        for led_index in range(self.led_count):
            base = self.channel_offset + led_index * 3
            if base + 2 >= len(data):
                break
            r = data[base]
            g = data[base + 1]
            b = data[base + 2]
            self.set_led_rgb(led_index, r, g, b)