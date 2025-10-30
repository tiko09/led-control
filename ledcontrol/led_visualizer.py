# led-control WS2812B LED Controller Server
# Copyright 2025 jackw01. Released under the MIT License (see LICENSE for details).

import time
import threading
import logging
import numpy as np
from flask_socketio import SocketIO, emit

logger = logging.getLogger(__name__)

class LEDVisualizer:
    """
    Streams LED pixel data to connected web clients via WebSocket
    at a throttled rate (default 30 FPS) for visualization
    """
    
    def __init__(self, socketio, target_fps=30):
        self.socketio = socketio
        self.target_fps = target_fps
        self.frame_interval = 1.0 / target_fps
        
        self.enabled = False
        self.connected_clients = 0
        self.last_frame_time = 0
        self.current_pixels = None
        self.lock = threading.Lock()
        
        # Statistics
        self.frames_sent = 0
        self.bytes_sent = 0
        
    def on_connect(self):
        """Called when a client connects to the visualizer"""
        with self.lock:
            self.connected_clients += 1
            self.enabled = self.connected_clients > 0
        logger.info(f'Client connected (total: {self.connected_clients})')
        
    def on_disconnect(self):
        """Called when a client disconnects"""
        with self.lock:
            self.connected_clients = max(0, self.connected_clients - 1)
            self.enabled = self.connected_clients > 0
        logger.info(f'Client disconnected (remaining: {self.connected_clients})')
        
    def update_pixels(self, pixels, led_count, mode='rgb'):
        """
        Called from the animation controller to update pixel data
        
        Args:
            pixels: List of tuples [(r,g,b), (r,g,b), ...] or [(h,s,v), ...]
            led_count: Number of LEDs
            mode: 'rgb' or 'hsv'
        """
        if not self.enabled or self.connected_clients == 0:
            return
            
        current_time = time.perf_counter()
        
        # Throttle to target FPS
        if current_time - self.last_frame_time < self.frame_interval:
            return
            
        self.last_frame_time = current_time
        
        # Convert to RGB uint8 array for efficient transmission
        try:
            if mode == 'hsv':
                # Convert HSV to RGB
                rgb_pixels = self._hsv_to_rgb_batch(pixels)
            else:
                # Already RGB, just scale to 0-255
                rgb_pixels = np.array(pixels, dtype=np.float32)
                rgb_pixels = np.clip(rgb_pixels * 255.0, 0, 255).astype(np.uint8)
            
            # Flatten to 1D array for compact transmission
            pixel_data = rgb_pixels.ravel().tolist()
            
            # Send to all connected clients
            self.socketio.emit('led_frame', {
                'pixels': pixel_data,
                'count': led_count,
                'timestamp': current_time
            }, namespace='/visualizer')
            
            self.frames_sent += 1
            self.bytes_sent += len(pixel_data)
            
            if self.frames_sent % 100 == 0:
                avg_fps = 1.0 / self.frame_interval if self.frame_interval > 0 else 0
                logger.debug(f'{self.frames_sent} frames sent, '
                            f'{self.bytes_sent / 1024:.1f} KB, '
                            f'~{avg_fps:.1f} FPS')
                      
        except Exception as e:
            logger.error(f'Error sending frame: {e}', exc_info=True)
    
    def _hsv_to_rgb_batch(self, hsv_pixels):
        """Convert HSV colors to RGB (vectorized for performance)"""
        hsv_array = np.array(hsv_pixels, dtype=np.float32)
        h = hsv_array[:, 0]
        s = hsv_array[:, 1]
        v = hsv_array[:, 2]
        
        # Ensure H is in [0, 1] range
        h = np.fmod(h, 1.0)
        
        # HSV to RGB conversion
        i = (h * 6.0).astype(np.int32)
        f = h * 6.0 - i
        
        p = v * (1.0 - s)
        q = v * (1.0 - f * s)
        t = v * (1.0 - (1.0 - f) * s)
        
        i = i % 6
        
        # Initialize RGB array
        rgb = np.zeros((len(hsv_pixels), 3), dtype=np.float32)
        
        # Map based on i value
        mask = (i == 0)
        rgb[mask] = np.column_stack([v[mask], t[mask], p[mask]])
        
        mask = (i == 1)
        rgb[mask] = np.column_stack([q[mask], v[mask], p[mask]])
        
        mask = (i == 2)
        rgb[mask] = np.column_stack([p[mask], v[mask], t[mask]])
        
        mask = (i == 3)
        rgb[mask] = np.column_stack([p[mask], q[mask], v[mask]])
        
        mask = (i == 4)
        rgb[mask] = np.column_stack([t[mask], p[mask], v[mask]])
        
        mask = (i == 5)
        rgb[mask] = np.column_stack([v[mask], p[mask], q[mask]])
        
        # Scale to 0-255
        rgb = np.clip(rgb * 255.0, 0, 255).astype(np.uint8)
        
        return rgb
    
    def get_stats(self):
        """Return visualizer statistics"""
        return {
            'enabled': self.enabled,
            'connected_clients': self.connected_clients,
            'target_fps': self.target_fps,
            'frames_sent': self.frames_sent,
            'bytes_sent': self.bytes_sent,
        }
