# led-control WS2812B LED Controller Server
# Copyright 2025 jackw01. Released under the MIT License (see LICENSE for details).

import socket
import logging
import time
import threading
from zeroconf import ServiceInfo, Zeroconf, ServiceBrowser, ServiceStateChange
from typing import Dict, List, Optional, Callable

logger = logging.getLogger(__name__)


class PiInfo:
    """Information about a discovered Pi"""
    def __init__(self, name: str, hostname: str, port: int, addresses: List[str], 
                 device_name: str = "", group: str = "", version: str = ""):
        self.name = name  # Service name (unique)
        self.hostname = hostname
        self.port = port
        self.addresses = addresses  # Can have multiple IPs
        self.device_name = device_name or name  # User-friendly name
        self.group = group
        self.version = version
        self.last_seen = time.time()
        self.online = True
        
    @property
    def primary_address(self) -> str:
        """Returns the first IPv4 address"""
        return self.addresses[0] if self.addresses else ""
    
    @property
    def url(self) -> str:
        """Returns the full URL to access this Pi"""
        return f"http://{self.primary_address}:{self.port}"
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return {
            'name': self.name,
            'hostname': self.hostname,
            'port': self.port,
            'addresses': self.addresses,
            'device_name': self.device_name,
            'group': self.group,
            'version': self.version,
            'url': self.url,
            'last_seen': self.last_seen,
            'online': self.online,
        }


class PiDiscoveryService:
    """
    Service for discovering other LED Control instances on the network
    using mDNS/Zeroconf
    """
    
    SERVICE_TYPE = "_ledcontrol._tcp.local."
    
    def __init__(self, port: int = 80, device_name: str = "", group: str = "", 
                 version: str = "2.0.0", on_device_change: Optional[Callable] = None):
        self.port = port
        self.device_name = device_name or socket.gethostname()
        self.group = group
        self.version = version
        self.on_device_change = on_device_change  # Callback when devices change
        
        self.zeroconf = None
        self.service_info = None
        self.browser = None
        
        # Dictionary of discovered devices: {service_name: PiInfo}
        self.devices: Dict[str, PiInfo] = {}
        self.lock = threading.Lock()
        
        # Health check thread
        self._running = False
        self._health_thread = None
        
    def start(self):
        """Start the discovery service"""
        try:
            self.zeroconf = Zeroconf()
            
            # Register our own service
            self._register_service()
            
            # Start browsing for other services
            self.browser = ServiceBrowser(
                self.zeroconf, 
                self.SERVICE_TYPE, 
                handlers=[self._on_service_state_change]
            )
            
            # Start health check thread
            self._running = True
            self._health_thread = threading.Thread(target=self._health_check_loop, daemon=True)
            self._health_thread.start()
            
            logger.info(f"Pi Discovery Service started: {self.device_name} ({self.group})")
            
        except Exception as e:
            logger.error(f"Failed to start Pi Discovery Service: {e}", exc_info=True)
    
    def stop(self):
        """Stop the discovery service"""
        self._running = False
        
        if self._health_thread:
            self._health_thread.join(timeout=2)
        
        if self.zeroconf:
            if self.service_info:
                self.zeroconf.unregister_service(self.service_info)
            self.zeroconf.close()
            
        logger.info("Pi Discovery Service stopped")
    
    def _register_service(self):
        """Register our own service for others to discover"""
        # Get local IP addresses
        hostname = socket.gethostname()
        addresses = []
        
        try:
            # Try to get the primary network interface IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            addresses.append(socket.inet_aton(s.getsockname()[0]))
            s.close()
        except Exception:
            pass
        
        # Fallback to localhost if no network interface found
        if not addresses:
            addresses.append(socket.inet_aton("127.0.0.1"))
        
        # Create service info
        service_name = f"{self.device_name}.{self.SERVICE_TYPE}"
        
        properties = {
            'device_name': self.device_name.encode('utf-8'),
            'group': self.group.encode('utf-8'),
            'version': self.version.encode('utf-8'),
        }
        
        self.service_info = ServiceInfo(
            self.SERVICE_TYPE,
            service_name,
            addresses=addresses,
            port=self.port,
            properties=properties,
            server=f"{hostname}.local.",
        )
        
        self.zeroconf.register_service(self.service_info)
        logger.info(f"Registered service: {service_name}")
    
    def _on_service_state_change(self, zeroconf: Zeroconf, service_type: str, 
                                  name: str, state_change: ServiceStateChange):
        """Callback when a service is added, updated, or removed"""
        
        if state_change is ServiceStateChange.Added:
            self._on_service_added(zeroconf, service_type, name)
        elif state_change is ServiceStateChange.Removed:
            self._on_service_removed(name)
        elif state_change is ServiceStateChange.Updated:
            self._on_service_updated(zeroconf, service_type, name)
    
    def _on_service_added(self, zeroconf: Zeroconf, service_type: str, name: str):
        """Handle newly discovered service"""
        info = zeroconf.get_service_info(service_type, name)
        
        if info:
            # Don't add ourselves
            if self.service_info and name == self.service_info.name:
                return
            
            # Parse properties
            props = info.properties or {}
            device_name = props.get(b'device_name', b'').decode('utf-8')
            group = props.get(b'group', b'').decode('utf-8')
            version = props.get(b'version', b'').decode('utf-8')
            
            # Convert addresses to string format
            addresses = [socket.inet_ntoa(addr) for addr in info.addresses]
            
            pi_info = PiInfo(
                name=name,
                hostname=info.server.rstrip('.'),
                port=info.port,
                addresses=addresses,
                device_name=device_name,
                group=group,
                version=version
            )
            
            with self.lock:
                self.devices[name] = pi_info
            
            logger.info(f"Discovered Pi: {device_name} ({pi_info.primary_address}:{info.port})")
            
            if self.on_device_change:
                self.on_device_change('added', pi_info)
    
    def _on_service_removed(self, name: str):
        """Handle service removal"""
        with self.lock:
            if name in self.devices:
                pi_info = self.devices[name]
                pi_info.online = False
                logger.info(f"Pi went offline: {pi_info.device_name}")
                
                if self.on_device_change:
                    self.on_device_change('removed', pi_info)
                
                # Keep in list for a while (will be cleaned up by health check)
    
    def _on_service_updated(self, zeroconf: Zeroconf, service_type: str, name: str):
        """Handle service update"""
        # Re-add with updated info
        self._on_service_added(zeroconf, service_type, name)
    
    def _health_check_loop(self):
        """Periodically check health of discovered devices"""
        while self._running:
            time.sleep(30)  # Check every 30 seconds
            
            with self.lock:
                current_time = time.time()
                to_remove = []
                
                for name, pi_info in self.devices.items():
                    # Remove devices that haven't been seen for 2 minutes
                    if not pi_info.online and (current_time - pi_info.last_seen) > 120:
                        to_remove.append(name)
                        logger.info(f"Removing stale device: {pi_info.device_name}")
                
                for name in to_remove:
                    del self.devices[name]
    
    def get_devices(self) -> List[PiInfo]:
        """Get list of all discovered devices"""
        with self.lock:
            return list(self.devices.values())
    
    def get_device(self, name: str) -> Optional[PiInfo]:
        """Get specific device by name"""
        with self.lock:
            return self.devices.get(name)
    
    def update_device_info(self, device_name: str = None, group: str = None):
        """Update our own device information"""
        if device_name:
            self.device_name = device_name
        if group is not None:
            self.group = group
        
        # Re-register service with new info
        if self.zeroconf and self.service_info:
            self.zeroconf.unregister_service(self.service_info)
            self._register_service()
            logger.info(f"Updated device info: {self.device_name} ({self.group})")
