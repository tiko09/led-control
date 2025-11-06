# led-control WS2812B LED Controller Server
# Copyright 2021 jackw01. Released under the MIT License (see LICENSE for details).
 
import io
import math

def get_raspberry_pi_version():
    """
    Detect Raspberry Pi model and return version number.
    Returns: 5 for Pi 5, 3 for Pi 3/4, 0 for non-Pi systems
    """
    try:
        with io.open('/sys/firmware/devicetree/base/model', 'r') as m:
            model = m.read().lower()
            if 'raspberry pi 5' in model:
                return 5
            elif 'raspberry pi' in model:
                return 3
    except Exception:
        pass
    return 0

def is_raspberrypi():
    """Check if running on any Raspberry Pi"""
    return get_raspberry_pi_version() > 0

# Always import utility functions - prefer C extension for performance, fallback to Python
# These are needed for animation calculations regardless of platform
try:
    # Try to import the C extension first (best performance)
    from . import ledcontrol_animation_utils as c_utils
    
    # Wrap C functions for consistent API
    float_to_int_1000 = c_utils.float_to_int_1000
    float_to_int_1000_mirror = c_utils.float_to_int_1000_mirror
    wave_pulse = c_utils.wave_pulse
    wave_triangle = c_utils.wave_triangle
    wave_sine = c_utils.wave_sine
    wave_cubic = c_utils.wave_cubic
    plasma_sines = c_utils.plasma_sines
    plasma_sines_octave = c_utils.plasma_sines_octave
    perlin_noise_3d = c_utils.perlin_noise_3d
    fbm_noise_3d = c_utils.fbm_noise_3d
    
    def blackbody_to_rgb(kelvin):
        """Wrapper for C function that returns a list instead of struct"""
        result = c_utils.blackbody_to_rgb(kelvin)
        return [result.r, result.g, result.b]
    
    def blackbody_correction_rgb(rgb, kelvin):
        """Wrapper for C function"""
        # Convert Python list to C struct-like input
        bb = c_utils.blackbody_to_rgb(kelvin)
        return [rgb[0] * bb.r, rgb[1] * bb.g, rgb[2] * bb.b]
    
    print("Using C extension for animation utilities (high performance)")
    
except ImportError as e:
    # C extension not available, try Python with pyfastnoisesimd
    try:
        import pyfastnoisesimd as fns
        # Import all utility functions that are used by animationcontroller.py
        from .driver_non_raspberry_pi import (
            float_to_int_1000,
            float_to_int_1000_mirror,
            wave_pulse,
            wave_triangle,
            wave_sine,
            wave_cubic,
            plasma_sines,
            plasma_sines_octave,
            perlin_noise_3d,
            fbm_noise_3d,
            blackbody_to_rgb,
            blackbody_correction_rgb
        )
        print("Using Python implementation with pyfastnoisesimd for animation utilities")
    except ImportError:
        # pyfastnoisesimd not available either (expected on Raspberry Pi without C extension)
        # Define simplified versions of these functions
        print("Warning: Using simplified Python fallback for animation utilities (reduced performance)")
    def float_to_int_1000(t):
        return int(t * 999.9) % 1000
    
    def float_to_int_1000_mirror(t):
        return abs(int(t * 1998.9) % 1999 - 999)
    
    def wave_pulse(t, duty_cycle):
        return math.ceil(duty_cycle - math.fmod(t, 1.0))
    
    def wave_triangle(t):
        ramp = math.fmod((2.0 * t), 2.0)
        return math.fabs((ramp + 2.0 if ramp < 0 else ramp) - 1.0)
    
    def wave_sine(t):
        return math.cos(6.283 * t) / 2.0 + 0.5
    
    def wave_cubic(t):
        ramp = math.fmod((2.0 * t), 2.0)
        tri = math.fabs((ramp + 2.0 if ramp < 0 else ramp) - 1.0)
        if tri > 0.5:
            t2 = 1.0 - tri
            return 1.0 - 4.0 * t2 * t2 * t2
        else:
            return 4.0 * tri * tri * tri
    
    def plasma_sines(x, y, t, coeff_x, coeff_y, coeff_x_y, coeff_dist_x_y):
        v = 0
        v += math.sin((x + t) * coeff_x)
        v += math.sin((y + t) * coeff_y)
        v += math.sin((x + y + t) * coeff_x_y)
        v += math.sin((math.sqrt(x * x + y * y) + t) * coeff_dist_x_y)
        return v
    
    def plasma_sines_octave(x, y, t, octaves, lacunarity, persistence):
        vx = x
        vy = y
        freq = 1.0
        amplitude = 1.0
        for i in range(octaves):
            vx1 = vx
            vx += math.cos(vy * freq + t * freq) * amplitude
            vy += math.sin(vx1 * freq + t * freq) * amplitude
            freq *= lacunarity
            amplitude *= persistence
        return vx / 2.0
    
    def perlin_noise_3d(x, y, z):
        # Simplified fallback - just return 0 array
        # Real noise requires pyfastnoisesimd
        import numpy as np
        return np.zeros_like(x)
    
    def fbm_noise_3d(x, y, z, octaves, lacunarity, persistence):
        # Simplified fallback
        import numpy as np
        return np.zeros_like(x)
    
    def blackbody_to_rgb(kelvin):
        tmp_internal = kelvin / 100.0
        r_out = 0
        g_out = 0
        b_out = 0

        def clamp_local(val, min_val, max_val):
            return max(min_val, min(max_val, val))

        if tmp_internal <= 66:
            xg = tmp_internal - 2.0
            r_out = 1.0
            g_out = clamp_local((-155.255 - 0.446 * xg + 104.492 * math.log(xg)) / 255.0, 0, 1)
        else:
            xr = tmp_internal - 55.0
            xg = tmp_internal - 50.0
            r_out = clamp_local((351.977 + 0.114 * xr - 40.254 * math.log(xr)) / 255.0, 0, 1)
            g_out = clamp_local((325.449 + 0.079 * xg - 28.085 * math.log(xg)) / 255.0, 0, 1)

        if tmp_internal >= 66:
            b_out = 1.0
        elif tmp_internal <= 19:
            b_out = 0.0
        else:
            xb = tmp_internal - 10.0
            b_out = clamp_local((-254.769 + 0.827 * xb + 115.680 * math.log(xb)) / 255.0, 0, 1)

        return [r_out, g_out, b_out]
    
    def blackbody_correction_rgb(rgb, kelvin):
        bb = blackbody_to_rgb(kelvin)
        return [rgb[0] * bb[0], rgb[1] * bb[1], rgb[2] * bb[2]]

# Get Pi version once at module import time
pi_version = get_raspberry_pi_version()

if pi_version == 5:
    # Raspberry Pi 5: Use SPI-based driver from our RGBW-capable fork
    try:
        # Try to import from the submodule first (development setup)
        import sys
        import os
        submodule_path = os.path.join(os.path.dirname(__file__), 'rpi5-ws2812-rgbw', 'src')
        if os.path.exists(submodule_path) and submodule_path not in sys.path:
            sys.path.insert(0, submodule_path)
        
        from rpi5_ws2812.ws2812 import Color, WS2812SpiDriver as _WS2812SpiDriver
        print("Using rpi5-ws2812-rgbw driver for Raspberry Pi 5 (SPI-based, RGBW-capable)")
        
        # Strip type constants (compatible with rpi_ws281x)
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
        
        # Compatibility wrapper class for rpi5-ws2812-rgbw
        class WS2811Wrapper:
            """
            Wrapper for rpi5-ws2812-rgbw's Strip to provide rpi_ws281x-like API
            Now uses the native RGBW support from the driver instead of manual SPI encoding
            """
            def __init__(self, led_count, led_pin, led_freq, led_dma, led_invert, led_brightness, led_channel, strip_type):
                # rpi5-ws2812 uses SPI, so led_pin/led_freq/led_dma/led_invert are ignored
                self.led_count = led_count
                self.strip_type = strip_type
                self.has_white = (strip_type & 0x18000000) != 0
                # Note: Don't set brightness in the driver - it's already applied in render functions
                # to avoid double-scaling which causes flickering
                
                try:
                    # Use the RGBW-capable driver from our fork
                    self.driver = _WS2812SpiDriver(
                        spi_bus=0, 
                        spi_device=0, 
                        led_count=led_count,
                        has_white=self.has_white
                    )
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
            
            def begin(self):
                """Initialize - no-op for rpi5-ws2812 (already initialized in constructor)"""
                return 0
            
            def show(self):
                """Write pixel buffer to LED strip"""
                self.strip.show()
            
            def setPixelColor(self, index, color):
                """Set pixel color from packed 32-bit RGBW value"""
                # Unpack color: format is 0xWWRRGGBB
                w = (color >> 24) & 0xFF
                r = (color >> 16) & 0xFF
                g = (color >> 8) & 0xFF
                b = color & 0xFF
                
                # Create Color object (will use all 4 channels for RGBW, ignore w for RGB)
                self.strip.set_pixel_color(index, Color(r, g, b, w))
            
            def getPixelColor(self, index):
                """Get pixel color as packed 32-bit RGBW value"""
                # Note: rpi5-ws2812 doesn't support reading back pixel values
                # This is a limitation of the SPI-based approach
                return 0
            
            def numPixels(self):
                """Get number of pixels"""
                return self.led_count
            
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
        
        # Color temperature to RGB conversion (approximation)
        def color_temp_to_rgb(kelvin):
            """
            Convert color temperature in Kelvin to RGB values (0-255)
            Based on Tanner Helland's algorithm
            """
            temp = kelvin / 100.0
            
            # Red
            if temp <= 66:
                r = 255
            else:
                r = temp - 60
                r = 329.698727446 * (r ** -0.1332047592)
                r = max(0, min(255, r))
            
            # Green
            if temp <= 66:
                g = temp
                g = 99.4708025861 * (g ** 0.07551484922) - 161.1195681661
            else:
                g = temp - 60
                g = 288.1221695283 * (g ** -0.0755148492)
            g = max(0, min(255, g))
            
            # Blue
            if temp >= 66:
                b = 255
            else:
                if temp <= 19:
                    b = 0
                else:
                    b = temp - 10
                    b = 138.5177312231 * (b ** 0.0767114632) - 305.0447927307
                    b = max(0, min(255, b))
            
            return (int(r), int(g), int(b))
        
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
        def render_rgb_float(rgb, corr_rgb, saturation, brightness, has_white, white_temp=5000, rgbw_algorithm='legacy'):
            """Convert RGB float to packed RGBW"""
            r = clamp(rgb[0], 0.0, 1.0)
            g = clamp(rgb[1], 0.0, 1.0)
            b = clamp(rgb[2], 0.0, 1.0)
            w = 0.0
            sat = int(saturation * 255)
            
            if has_white:
                if rgbw_algorithm == 'advanced':
                    # Advanced algorithm: Extract minimum RGB value to white channel
                    # and compensate for white LED color temperature
                    min_val = min(r, g, b)
                    
                    if min_val > 0:
                        # Get white LED color as RGB
                        white_r, white_g, white_b = color_temp_to_rgb(white_temp)
                        white_r /= 255.0
                        white_g /= 255.0
                        white_b /= 255.0
                        
                        # Normalize white color
                        white_max = max(white_r, white_g, white_b)
                        if white_max > 0:
                            white_r /= white_max
                            white_g /= white_max
                            white_b /= white_max
                        
                        # Extract white and compensate RGB
                        w = min_val
                        r = r - (w * white_r)
                        g = g - (w * white_g)
                        b = b - (w * white_b)
                        
                        # Clamp to valid range
                        r = max(0.0, r)
                        g = max(0.0, g)
                        b = max(0.0, b)
                    
                    # Apply saturation to white channel
                    if sat != 255:
                        if sat == 0:
                            # Full desaturation: all white
                            avg = (r + g + b) / 3.0
                            r, g, b = 0, 0, 0
                            w = avg + w
                        else:
                            # Partial desaturation
                            avg = (r + g + b) / 3.0
                            desat_factor = (255 - sat) / 255.0
                            r = r * (sat / 255.0) + avg * desat_factor
                            g = g * (sat / 255.0) + avg * desat_factor
                            b = b * (sat / 255.0) + avg * desat_factor
                            w = w + (avg * desat_factor * desat_factor)
                else:
                    # Legacy algorithm: Uses desaturation
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
        def ws2811_hsv_render_range_float(channel, values, start, end, correction, saturation, brightness, gamma, has_white, white_temp=5000, rgbw_algorithm='legacy'):
            """Render HSV values to a range of LEDs"""
            if channel is None or end > channel.numPixels():
                return
            corr_rgb = unpack_rgb(correction)
            for i in range(start, end):
                color = render_hsv2rgb_rainbow_float(values[i - start], corr_rgb, saturation, brightness, has_white)
                channel.setPixelColor(i, color)
        
        def ws2811_rgb_render_range_float(channel, values, start, end, correction, saturation, brightness, gamma, has_white, white_temp=5000, rgbw_algorithm='legacy'):
            """Render RGB values to a range of LEDs"""
            if channel is None or end > channel.numPixels():
                return
            corr_rgb = unpack_rgb(correction)
            for i in range(start, end):
                color = render_rgb_float(values[i - start], corr_rgb, saturation, brightness, has_white, white_temp, rgbw_algorithm)
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
        print(f"Error: Could not import rpi5_ws2812 on Raspberry Pi 5: {e}")
        print("Install with: pip install rpi5-ws2812")
        # Fallback to non-Pi driver
        from .driver_non_raspberry_pi import WS2811Wrapper

elif pi_version == 3:
    # Raspberry Pi 3/4: Use PWM-based driver
    # Try custom SWIG wrapper first (provides full C API access)
    try:
        from ledcontrol.driver.ledcontrol_rpi_ws281x_driver import (
            WS2811_STRIP_RGB, WS2811_STRIP_RBG, WS2811_STRIP_GRB,
            WS2811_STRIP_GBR, WS2811_STRIP_BRG, WS2811_STRIP_BGR,
            SK6812_STRIP_RGBW, SK6812_STRIP_RBGW, SK6812_STRIP_GRBW,
            SK6812_STRIP_GBRW, SK6812_STRIP_BRGW, SK6812_STRIP_BGRW,
            ws2811_led_t, new_ws2811_t, ws2811_channel_get,
            ws2811_channel_t_count_set, ws2811_channel_t_gpionum_set,
            ws2811_channel_t_invert_set, ws2811_channel_t_brightness_set,
            ws2811_channel_t_strip_type_set, ws2811_channel_t_gamma_set,
            ws2811_t_freq_set, ws2811_t_dmanum_set,
            ws2811_init, ws2811_fini, ws2811_render,
            ws2811_led_set, ws2811_led_get,
            ws2811_get_return_t_str, delete_ws2811_t
        )
        print("Using custom rpi_ws281x driver for Raspberry Pi 3/4 (PWM-based, high performance)")
        
        # Wrapper class using custom SWIG bindings
        class WS2811Wrapper:
            """High-performance wrapper using custom SWIG bindings"""
            def __init__(self, led_count, led_pin, led_freq, led_dma, led_invert, led_brightness, led_channel, strip_type):
                self.led_count = led_count
                self.strip_type = strip_type
                self.has_white = (strip_type & 0x18000000) != 0
                self._channel = led_channel
                
                # Create and initialize the ws2811_t structure
                self._leds = new_ws2811_t()
                
                # Get the channel
                channel = ws2811_channel_get(self._leds, led_channel)
                
                # Configure the channel
                ws2811_channel_t_count_set(channel, led_count)
                ws2811_channel_t_gpionum_set(channel, led_pin)
                ws2811_channel_t_invert_set(channel, led_invert)
                ws2811_channel_t_brightness_set(channel, led_brightness)
                ws2811_channel_t_strip_type_set(channel, strip_type)
                
                # Configure the device
                ws2811_t_freq_set(self._leds, led_freq)
                ws2811_t_dmanum_set(self._leds, led_dma)
            
            def begin(self):
                return ws2811_init(self._leds)
            
            def show(self):
                ws2811_render(self._leds)
            
            def setPixelColor(self, index, color):
                ws2811_led_set(self._leds, self._channel, index, color)
            
            def getPixelColor(self, index):
                return ws2811_led_get(self._leds, self._channel, index)
            
            def setBrightness(self, brightness):
                channel = ws2811_channel_get(self._leds, self._channel)
                ws2811_channel_t_brightness_set(channel, brightness)
            
            def getBrightness(self):
                channel = ws2811_channel_get(self._leds, self._channel)
                # Note: getBrightness not available in C API, return default
                return 255
            
            def cleanup(self):
                ws2811_fini(self._leds)
                delete_ws2811_t(self._leds)
    
    except ImportError as e:
        # Fallback to standard PyPI rpi_ws281x package
        print(f"Custom rpi_ws281x wrapper not available: {e}")
        print("Falling back to standard rpi_ws281x PyPI package")
        try:
            from rpi_ws281x import PixelStrip, Color
            from rpi_ws281x import (
                WS2811_STRIP_RGB, WS2811_STRIP_RBG, WS2811_STRIP_GRB,
                WS2811_STRIP_GBR, WS2811_STRIP_BRG, WS2811_STRIP_BGR,
                SK6812_STRIP_RGBW, SK6812_STRIP_RBGW, SK6812_STRIP_GRBW,
                SK6812_STRIP_GBRW, SK6812_STRIP_BRGW, SK6812_STRIP_BGRW,
            )
            print("Using rpi_ws281x driver for Raspberry Pi 3/4 (PWM-based)")
            
            # Wrapper class to provide consistent API
            class WS2811Wrapper:
                """Wrapper for rpi_ws281x PixelStrip"""
                def __init__(self, led_count, led_pin, led_freq, led_dma, led_invert, led_brightness, led_channel, strip_type):
                    self.strip = PixelStrip(
                        led_count,
                        led_pin,
                        led_freq,
                        led_dma,
                        led_invert,
                        led_brightness,
                        led_channel,
                        strip_type
                    )
                    self.led_count = led_count
                    self.strip_type = strip_type
                    self.has_white = (strip_type & 0x18000000) != 0
                
                def begin(self):
                    self.strip.begin()
                    return 0
                
                def show(self):
                    self.strip.show()
                
                def setPixelColor(self, index, color):
                    self.strip.setPixelColor(index, color)
                
                def getPixelColor(self, index):
                    return self.strip.getPixelColor(index)
                
                def setBrightness(self, brightness):
                    self.strip.setBrightness(brightness)
                
                def getBrightness(self):
                    return self.strip.getBrightness()
                
                def cleanup(self):
                    pass  # rpi_ws281x handles cleanup automatically
            
            # Add Python implementations of render functions for compatibility
            # (same as Pi 5 implementations)
            def clamp(val, min_val, max_val):
                return max(min_val, min(max_val, val))
            
            def scale_8(val, scale):
                return int((val * scale) >> 8)
            
            def pack_rgbw(r, g, b, w):
                return ((w & 0xFF) << 24) | ((r & 0xFF) << 16) | ((g & 0xFF) << 8) | (b & 0xFF)
            
            def unpack_rgb(color):
                return [(color >> 16) & 0xFF, (color >> 8) & 0xFF, color & 0xFF]
            
            def render_hsv2rgb_rainbow_float(hsv, corr_rgb, saturation, brightness, has_white):
                """Convert HSV float to packed RGBW using rainbow spectrum"""
                import colorsys
                h, s, v = hsv
                r, g, b = colorsys.hsv_to_rgb(h, s * saturation, v * brightness)
                r8 = scale_8(int(r * 255), corr_rgb[0])
                g8 = scale_8(int(g * 255), corr_rgb[1])
                b8 = scale_8(int(b * 255), corr_rgb[2])
                if has_white:
                    return pack_rgbw(r8, g8, b8, 0)
                else:
                    return ((r8 & 0xFF) << 16) | ((g8 & 0xFF) << 8) | (b8 & 0xFF)
            
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
            
            def ws2811_hsv_render_range_float(channel, values, start, end, correction, saturation, brightness, gamma, has_white):
                """Render HSV values to a range of LEDs"""
                if channel is None:
                    return
                corr_rgb = unpack_rgb(correction)
                for i in range(start, end):
                    color = render_hsv2rgb_rainbow_float(values[i - start], corr_rgb, saturation, brightness, has_white)
                    channel.setPixelColor(i, color)
            
            def ws2811_rgb_render_range_float(channel, values, start, end, correction, saturation, brightness, gamma, has_white):
                """Render RGB values to a range of LEDs"""
                if channel is None:
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
                    strip.show()
                return 1
            
            def ws2811_render(strip):
                """Render/update LEDs"""
                if strip is not None:
                    strip.show()
        
        except ImportError as e2:
            print(f"Error: Could not import rpi_ws281x on Raspberry Pi 3/4: {e2}")
            print("Install with: pip install rpi_ws281x")
            # Fallback to non-Pi driver
            from .driver_non_raspberry_pi import WS2811Wrapper
            # Need to import strip type constants for simulation mode
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

else:
    # Non-Raspberry Pi system: Use simulation driver
    print("Non-Raspberry Pi system detected - using simulation mode")
    from .driver_non_raspberry_pi import WS2811Wrapper
