# led-control WS2812B LED Controller Server
# Copyright 2021 jackw01. Released under the MIT License (see LICENSE for details).
 
import io
import math

def is_raspberrypi():
    try:
        with io.open('/sys/firmware/devicetree/base/model', 'r') as m:
            if 'raspberry pi' in m.read().lower():
                return True
    except Exception:
        pass
    return False

if is_raspberrypi():
    try:
        from rpi5_ws2812.ws2812 import Color, WS2812SpiDriver
        
        # Strip type constants (compatible with rpi_ws281x)
        # Note: rpi5-ws2812 doesn't use these, but we keep them for compatibility
        WS2811_STRIP_RGB = 0x00100800
        WS2811_STRIP_RBG = 0x00100008
        WS2811_STRIP_GRB = 0x00081000
        WS2811_STRIP_GBR = 0x00080010
        WS2811_STRIP_BRG = 0x00001008
        WS2811_STRIP_BGR = 0x00000810
        SK6812_STRIP_RGBW = 0x18100800
        SK6812_STRIP_RBGW = 0x18100008
        SK6812_STRIP_GRBW = 0x18081000
        SK6812_STRIP_GBRW = 0x18080010
        SK6812_STRIP_BRGW = 0x18001008
        SK6812_STRIP_BGRW = 0x18000810
        
        # Helper functions for color packing/unpacking
        def pack_rgbw(r, g, b, w):
            """Pack RGBW values into a single 32-bit integer"""
            return ((w & 0xFF) << 24) | ((r & 0xFF) << 16) | ((g & 0xFF) << 8) | (b & 0xFF)
        
        def unpack_rgb(color):
            """Unpack RGB values from a 32-bit integer"""
            r = (color >> 16) & 0xFF
            g = (color >> 8) & 0xFF
            b = color & 0xFF
            return (r, g, b)
        
        def unpack_rgbw(color):
            """Unpack RGBW values from a 32-bit integer"""
            w = (color >> 24) & 0xFF
            r = (color >> 16) & 0xFF
            g = (color >> 8) & 0xFF
            b = color & 0xFF
            return (r, g, b, w)
        
        def scale_8(a, b):
            """Scale one 8-bit int by another (a * b / 255)"""
            return ((a & 0xFF) * (b & 0xFF)) >> 8
        
        def clamp(value, min_val, max_val):
            """Clamp value between min and max"""
            return max(min_val, min(max_val, value))
        
        # Compatibility wrapper class for rpi5-ws2812
        class WS2811Wrapper:
            """
            Wrapper for rpi5-ws2812's Strip to provide rpi_ws281x-like API
            Note: rpi5-ws2812 uses SPI, so led_pin/led_freq/led_dma are ignored
            """
            def __init__(self, led_count, led_pin, led_freq, led_dma, led_invert, led_brightness, led_channel, strip_type):
                # rpi5-ws2812 uses SPI, default to SPI bus 0, device 0
                # led_pin, led_freq, led_dma are ignored as they're GPIO/PWM specific
                try:
                    self.driver = WS2812SpiDriver(spi_bus=0, spi_device=0, led_count=led_count)
                    self.strip = self.driver.get_strip()
                except FileNotFoundError as e:
                    raise RuntimeError(
                        "SPI device not found. Please ensure:\n"
                        "1. SPI is enabled: Run 'sudo raspi-config' -> Interfacing Options -> SPI -> Enable\n"
                        "2. Your user is in the 'spidev' group: Run 'sudo adduser $USER spidev' and log out/in\n"
                        "3. The SPI device exists: Check 'ls -l /dev/spidev*'\n"
                        "4. You're running on a Raspberry Pi 5 (older models need the old version)\n"
                        f"Original error: {e}"
                    ) from e
                except PermissionError as e:
                    raise RuntimeError(
                        "Permission denied accessing SPI device. Please:\n"
                        "1. Add your user to the 'spidev' group: 'sudo adduser $USER spidev'\n"
                        "2. Log out and log back in for group changes to take effect\n"
                        "3. Or run with sudo (not recommended for security)\n"
                        f"Original error: {e}"
                    ) from e
                
                self.led_count = led_count
                self.strip_type = strip_type
                self.has_white = (strip_type & 0x18000000) != 0
                
                # Set initial brightness
                if led_brightness < 255:
                    self.strip.set_brightness(led_brightness / 255.0)
            
            def begin(self):
                """Initialize - no-op for rpi5-ws2812 (already initialized in constructor)"""
                return 0
            
            def show(self):
                """Write pixel buffer to LED strip"""
                self.strip.show()
            
            def setPixelColor(self, index, color):
                """Set pixel color from packed 32-bit RGBW value"""
                r, g, b, w = unpack_rgbw(color)
                # rpi5-ws2812 doesn't support white channel directly
                # For RGBW strips, we add white to RGB
                if self.has_white and w > 0:
                    r = min(255, r + w)
                    g = min(255, g + w)
                    b = min(255, b + w)
                self.strip.set_pixel_color(index, Color(r, g, b))
            
            def getPixelColor(self, index):
                """Get pixel color as packed 32-bit RGBW value - NOT IMPLEMENTED in rpi5-ws2812"""
                # rpi5-ws2812 doesn't support reading back pixel values
                return 0
            
            def numPixels(self):
                """Get number of pixels"""
                return self.strip.num_pixels()
            
            def cleanup(self):
                """Cleanup - clear the strip"""
                self.strip.clear()
        
        # Wrapper functions for compatibility with old driver API
        def new_ws2811_t():
            """Create a new ws2811_t structure (returns None, actual strip created in LEDController)"""
            return None
        
        def ws2811_channel_get(strip, channel):
            """Get channel from strip (returns the strip itself since we only use one channel)"""
            return strip
        
        def ws2811_channel_t_count_set(channel, count):
            """Set LED count (no-op, set during initialization)"""
            pass
        
        def ws2811_channel_t_gpionum_set(channel, gpio):
            """Set GPIO pin (no-op, rpi5-ws2812 uses SPI not GPIO)"""
            pass
        
        def ws2811_channel_t_invert_set(channel, invert):
            """Set invert flag (no-op, set during initialization)"""
            pass
        
        def ws2811_channel_t_brightness_set(channel, brightness):
            """Set brightness (no-op, set during initialization)"""
            pass
        
        def ws2811_channel_t_strip_type_set(channel, strip_type):
            """Set strip type (no-op, set during initialization)"""
            pass
        
        def ws2811_channel_t_gamma_set(channel, gamma):
            """Set gamma correction (no-op for now)"""
            pass
        
        def ws2811_t_freq_set(strip, freq):
            """Set frequency (no-op, rpi5-ws2812 uses fixed SPI frequency)"""
            pass
        
        def ws2811_t_dmanum_set(strip, dma):
            """Set DMA channel (no-op, rpi5-ws2812 doesn't use DMA)"""
            pass
        
        def ws2811_init(strip):
            """Initialize the strip"""
            if strip is not None and hasattr(strip, 'begin'):
                return strip.begin()
            return 0  # Success
        
        def ws2811_fini(strip):
            """Finalize/cleanup the strip"""
            if strip is not None and hasattr(strip, 'cleanup'):
                strip.cleanup()
        
        def ws2811_render(strip):
            """Render/show the LEDs"""
            if strip is not None and hasattr(strip, 'show'):
                strip.show()
        
        def ws2811_led_set(channel, index, color):
            """Set a single LED color"""
            if channel is not None and hasattr(channel, 'setPixelColor'):
                channel.setPixelColor(index, color)
            return 0
        
        def ws2811_led_get(channel, index):
            """Get a single LED color"""
            if channel is not None and hasattr(channel, 'getPixelColor'):
                return channel.getPixelColor(index)
            return 0
        
        def ws2811_get_return_t_str(code):
            """Get error string for return code"""
            return f"Error code {code}"
        
        def delete_ws2811_t(strip):
            """Delete ws2811_t structure (cleanup handled by Python GC)"""
            if strip is not None:
                ws2811_fini(strip)
        
        # HSV to RGB conversion (FastLED Rainbow algorithm)
        def render_hsv2rgb_rainbow_float(hsv, corr_rgb, saturation, brightness, has_white):
            """Convert HSV to RGB using FastLED's rainbow algorithm"""
            hue = int((hsv[0] % 1.0) * 255)
            sat = int(hsv[1] * saturation * 255)
            val = int((hsv[2] * hsv[2]) * 255)
            if 0 < val < 255:
                val += 1
            val = scale_8(val, int(brightness * 255))
            
            offset = hue & 0x1F
            offset8 = offset << 3
            third = offset8 // 3
            
            if not (hue & 0x80):
                if not (hue & 0x40):
                    if not (hue & 0x20):
                        r, g, b = 255 - third, third, 0
                    else:
                        r, g, b = 171, 85 + third, 0
                else:
                    if not (hue & 0x20):
                        r, g, b = 171 - third * 2, 170 + third, 0
                    else:
                        r, g, b = 0, 255 - third, third
            else:
                if not (hue & 0x40):
                    if not (hue & 0x20):
                        twothirds = third * 2
                        r, g, b = 0, 171 - twothirds, 85 + twothirds
                    else:
                        r, g, b = third, 0, 255 - third
                else:
                    if not (hue & 0x20):
                        r, g, b = 85 + third, 0, 171 - third
                    else:
                        r, g, b = 170 + third, 0, 85 - third
            
            w = 0
            if has_white:
                if sat != 255:
                    if sat == 0:
                        r, g, b, w = 0, 0, 0, 255
                    else:
                        desat = 255 - sat
                        desat = scale_8(desat, desat)
                        r = scale_8(r, sat)
                        g = scale_8(g, sat)
                        b = scale_8(b, sat)
                        w = desat
            else:
                if sat != 255:
                    if sat == 0:
                        r, g, b = 255, 255, 255
                    else:
                        desat = 255 - sat
                        desat = scale_8(desat, desat)
                        r = scale_8(r, sat) + desat
                        g = scale_8(g, sat) + desat
                        b = scale_8(b, sat) + desat
            
            if val != 255:
                if val == 0:
                    r, g, b, w = 0, 0, 0, 0
                else:
                    r = scale_8(r, val)
                    g = scale_8(g, val)
                    b = scale_8(b, val)
                    w = scale_8(w, val)
            
            r = scale_8(r, corr_rgb[0])
            g = scale_8(g, corr_rgb[1])
            b = scale_8(b, corr_rgb[2])
            
            return pack_rgbw(r, g, b, w)
        
        # RGB rendering
        def render_rgb_float(rgb, corr_rgb, saturation, brightness, has_white):
            """Convert RGB float to packed RGBW"""
            r = clamp(rgb[0], 0.0, 1.0)
            g = clamp(rgb[1], 0.0, 1.0)
            b = clamp(rgb[2], 0.0, 1.0)
            w = 0.0
            sat = int(saturation * 255)
            
            if has_white:
                max_val = max(r, g, b)
                if sat == 0:
                    r, g, b = 0, 0, 0
                    min_val = max_val
                else:
                    r = (r - max_val) * saturation + max_val
                    g = (g - max_val) * saturation + max_val
                    b = (b - max_val) * saturation + max_val
                    min_val = min(r, g, b)
                    r -= min_val
                    g -= min_val
                    b -= min_val
                w = min_val * min_val
            else:
                if sat != 255:
                    avg = (r + g + b) / 3.0
                    if sat == 0:
                        r = g = b = avg
                    else:
                        r = (r - avg) * saturation + avg
                        g = (g - avg) * saturation + avg
                        b = (b - avg) * saturation + avg
            
            r8 = int(r * brightness * 255)
            g8 = int(g * brightness * 255)
            b8 = int(b * brightness * 255)
            w8 = int(w * brightness * 255)
            
            r8 = scale_8(r8, corr_rgb[0])
            g8 = scale_8(g8, corr_rgb[1])
            b8 = scale_8(b8, corr_rgb[2])
            
            return pack_rgbw(r8, g8, b8, w8)
        
        # Render functions
        def ws2811_hsv_render_range_float(channel, values, start, end, correction, saturation, brightness, gamma, has_white):
            """Render HSV values to a range of LEDs"""
            if channel is None or end > channel.numPixels():
                return
            corr_rgb = unpack_rgb(correction)
            for i in range(start, end):
                color = render_hsv2rgb_rainbow_float(values[i - start], corr_rgb, saturation, brightness, has_white)
                channel.setPixelColor(i, color)
        
        def ws2811_rgb_render_range_float(channel, values, start, end, correction, saturation, brightness, gamma, has_white):
            """Render RGB values to a range of LEDs"""
            if channel is None or end > channel.numPixels():
                return
            corr_rgb = unpack_rgb(correction)
            for i in range(start, end):
                color = render_rgb_float(values[i - start], corr_rgb, saturation, brightness, has_white)
                channel.setPixelColor(i, color)
        
        def ws2811_rgb_render_calibration(strip, channel, count, correction, brightness):
            """Render calibration color to all LEDs"""
            if channel is None:
                return -1
            corr_rgb = unpack_rgb(correction)
            r8 = int(corr_rgb[0] * brightness)
            g8 = int(corr_rgb[1] * brightness)
            b8 = int(corr_rgb[2] * brightness)
            color = pack_rgbw(r8, g8, b8, 0)
            for i in range(count):
                channel.setPixelColor(i, color)
            if strip is not None:
                ws2811_render(strip)
            return 1
        
    except ImportError as e:
        print(f"Warning: Could not import rpi5_ws2812: {e}")
        from .driver_non_raspberry_pi import *
else:
    from .driver_non_raspberry_pi import *
