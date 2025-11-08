# sync_server.py
# Master/Slave animation synchronization via UDP broadcast
import socket
import struct
import threading
import logging
import time
from typing import Optional, Callable

SYNC_PORT = 6455  # Different from ArtNet (6454)
SYNC_MAGIC = b'LEDSYNC\x00'  # 8 bytes magic header

logger = logging.getLogger(__name__)


class AnimationSyncServer:
    """
    UDP-based animation time synchronization
    
    Master mode: Broadcasts current animation time to all devices on network
    Slave mode: Receives time updates and synchronizes local animation
    """
    
    def __init__(self, 
                 get_time_callback: Optional[Callable[[], float]] = None,
                 set_time_callback: Optional[Callable[[float], None]] = None,
                 master_mode: bool = False,
                 sync_interval: float = 0.5,  # 500ms default
                 broadcast_address: str = "255.255.255.255"):
        """
        Args:
            get_time_callback: Function to get current animation time (master mode)
            set_time_callback: Function to set animation time (slave mode)
            master_mode: If True, broadcasts time. If False, receives time.
            sync_interval: Seconds between sync broadcasts (master mode)
            broadcast_address: Broadcast IP address
        """
        self.get_time = get_time_callback
        self.set_time = set_time_callback
        self.master_mode = master_mode
        self.sync_interval = sync_interval
        self.broadcast_address = broadcast_address
        
        self._sock: Optional[socket.socket] = None
        self._thread: Optional[threading.Thread] = None
        self._running = threading.Event()
        self._sequence = 0  # Packet sequence number
        
        self.log = logging.getLogger("sync")
        
        # Statistics
        self._packets_sent = 0
        self._packets_received = 0
        self._last_sync_time = 0
        
    def start(self):
        """Start the sync server (master or slave)"""
        if self._thread and self._thread.is_alive():
            self.log.debug("Sync server already running")
            return
            
        self._running.set()
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        if self.master_mode:
            # Master: Enable broadcast
            self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            self._thread = threading.Thread(target=self._run_master, 
                                           name="SyncMaster", 
                                           daemon=True)
            self.log.info("🎬 Animation Sync MASTER started (broadcast every %.1fs)", 
                         self.sync_interval)
        else:
            # Slave: Bind to receive broadcasts
            self._sock.bind(('', SYNC_PORT))
            self._thread = threading.Thread(target=self._run_slave, 
                                           name="SyncSlave", 
                                           daemon=True)
            self.log.info("🎬 Animation Sync SLAVE started (listening on port %d)", 
                         SYNC_PORT)
        
        self._thread.start()
        
    def stop(self):
        """Stop the sync server"""
        self._running.clear()
        if self._sock:
            try:
                self._sock.close()
            except OSError:
                pass
        if self._thread:
            self._thread.join(timeout=1)
        
        if self.master_mode:
            self.log.info("Sync master stopped (sent %d packets)", self._packets_sent)
        else:
            self.log.info("Sync slave stopped (received %d packets)", self._packets_received)
    
    def _run_master(self):
        """Master thread: broadcast time periodically"""
        while self._running.is_set():
            try:
                if self.get_time:
                    current_time = self.get_time()
                    self._broadcast_time(current_time)
                    self._packets_sent += 1
                    
                    # Log every 10 packets (5 seconds at 500ms interval)
                    if self._packets_sent % 10 == 0:
                        self.log.debug("Master: broadcasted %d sync packets, current time: %.3fs", 
                                      self._packets_sent, current_time)
                
                # Sleep for sync interval
                time.sleep(self.sync_interval)
                
            except Exception as e:
                self.log.error("Error in master sync loop: %s", e)
                time.sleep(1)
    
    def _run_slave(self):
        """Slave thread: receive and apply time updates"""
        while self._running.is_set():
            try:
                data, addr = self._sock.recvfrom(1024)
                
                if not data.startswith(SYNC_MAGIC):
                    continue
                    
                if len(data) < 20:  # 8 (magic) + 4 (seq) + 8 (time)
                    continue
                
                # Parse packet
                sequence = struct.unpack_from("<I", data, 8)[0]
                sync_time = struct.unpack_from("<d", data, 12)[0]
                
                # Apply time
                if self.set_time:
                    self.set_time(sync_time)
                    self._packets_received += 1
                    self._last_sync_time = time.time()
                    
                    # Log every 10 packets
                    if self._packets_received % 10 == 0:
                        self.log.debug("Slave: received sync #%d, time: %.3fs from %s", 
                                      sequence, sync_time, addr[0])
                
            except OSError:
                if not self._running.is_set():
                    break
                continue
            except Exception as e:
                self.log.error("Error in slave sync loop: %s", e)
    
    def _broadcast_time(self, current_time: float):
        """Broadcast current animation time"""
        # Build packet: MAGIC(8) + SEQUENCE(4) + TIME(8)
        packet = bytearray(20)
        packet[0:8] = SYNC_MAGIC
        struct.pack_into("<I", packet, 8, self._sequence)
        struct.pack_into("<d", packet, 12, current_time)
        
        try:
            self._sock.sendto(packet, (self.broadcast_address, SYNC_PORT))
            self._sequence += 1
        except Exception as e:
            self.log.error("Failed to broadcast sync: %s", e)
    
    def get_stats(self) -> dict:
        """Get sync statistics"""
        return {
            'master_mode': self.master_mode,
            'running': self._running.is_set(),
            'packets_sent': self._packets_sent,
            'packets_received': self._packets_received,
            'last_sync_time': self._last_sync_time,
            'sync_interval': self.sync_interval
        }
