# led-control WS2812B LED Controller Server
# Copyright 2021 jackw01. Released under the MIT License (see LICENSE for details).

import atexit
import serial
import numpy as np
import itertools
import socket
import traceback
from enum import Enum

import ledcontrol.animationfunctions as animfunctions
import ledcontrol.driver as driver
import ledcontrol.utils as utils

class TargetMode(str, Enum):
    local = 'local'
    serial = 'serial'
    udp = 'udp'

class LEDController:
    def __init__(self,
                 led_count,
                 led_pin,
                 led_data_rate,
                 led_dma_channel,
                 led_pixel_order):
        if driver.is_raspberrypi():
            # This is bad but it's the only way
            px_order = driver.WS2811_STRIP_GRB
            if led_pixel_order == 'RGB':
                px_order = driver.WS2811_STRIP_RGB
            elif led_pixel_order == 'RBG':
                px_order = driver.WS2811_STRIP_RBG
            elif led_pixel_order == 'GRB':
                px_order = driver.WS2811_STRIP_GRB
            elif led_pixel_order == 'GBR':
                px_order = driver.WS2811_STRIP_GBR
            elif led_pixel_order == 'BRG':
                px_order = driver.WS2811_STRIP_BRG
            elif led_pixel_order == 'BGR':
                px_order = driver.WS2811_STRIP_BGR
            elif led_pixel_order == 'RGBW':
                px_order = driver.SK6812_STRIP_RGBW
            elif led_pixel_order == 'RBGW':
                px_order = driver.SK6812_STRIP_RBGW
            elif led_pixel_order == 'GRBW':
                px_order = driver.SK6812_STRIP_GRBW
            elif led_pixel_order == 'GBRW':
                px_order = driver.SK6812_STRIP_GBRW
            elif led_pixel_order == 'BRGW':
                px_order = driver.SK6812_STRIP_BRGW
            elif led_pixel_order == 'BGRW':
                px_order = driver.SK6812_STRIP_BGRW

            self._has_white = 1 if 'W' in led_pixel_order else 0
            self._count = led_count

            # Create ws2811_t structure and fill in parameters
            self._leds = driver.new_ws2811_t()

            # Initialize the channels to zero
            for i in range(2):
                chan = driver.ws2811_channel_get(self._leds, i)
                driver.ws2811_channel_t_count_set(chan, 0)
                driver.ws2811_channel_t_gpionum_set(chan, 0)
                driver.ws2811_channel_t_invert_set(chan, 0)
                driver.ws2811_channel_t_brightness_set(chan, 0)

            # Initialize the channel in use
            self._channel = driver.ws2811_channel_get(self._leds, 0) # default
            driver.ws2811_channel_t_gamma_set(self._channel, list(range(256)))
            driver.ws2811_channel_t_count_set(self._channel, led_count)
            driver.ws2811_channel_t_gpionum_set(self._channel, led_pin)
            driver.ws2811_channel_t_invert_set(self._channel, 0) # 1 if true
            driver.ws2811_channel_t_brightness_set(self._channel, 255)
            driver.ws2811_channel_t_strip_type_set(self._channel, px_order)

            # Initialize the controller
            driver.ws2811_t_freq_set(self._leds, led_data_rate)
            driver.ws2811_t_dmanum_set(self._leds, led_dma_channel)

            # Substitute for __del__, traps an exit condition and cleans up properly
            atexit.register(self._cleanup)

            # Begin
            resp = driver.ws2811_init(self._leds)
            if resp != 0:
                str_resp = driver.ws2811_get_return_t_str(resp)
                raise RuntimeError('ws2811_init failed with code {0} ({1})'.format(resp, str_resp))

        # Used for scaling values sent for remote rendering
        self._where_hue = np.zeros((led_count * 3,), dtype=bool)
        self._where_hue[0::3] = True

        self._targets_serial = {}
        self._targets_udp = {}

        self._udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def _cleanup(self):
        # Clean up memory used by the library when not needed anymore
        if driver.is_raspberrypi() and self._leds is not None:
            driver.delete_ws2811_t(self._leds)
            self._leds = None
            self._channel = None

    def set_range(self, pixels, start, end,
                  correction, saturation, brightness, color_mode,
                  render_mode, render_target):
        if render_mode == TargetMode.local:
            if driver.is_raspberrypi():
                if color_mode == animfunctions.ColorMode.hsv:
                    driver.ws2811_hsv_render_range_float(self._channel, pixels,
                                                         start, end,
                                                         correction, saturation,  brightness, 1.0,
                                                         self._has_white)
                else:
                    driver.ws2811_rgb_render_range_float(self._channel, pixels,
                                                         start, end,
                                                         correction, saturation,  brightness, 1.0,
                                                         self._has_white)
        else:
            data = np.fromiter(itertools.chain.from_iterable(pixels), np.float32)
            if color_mode == animfunctions.ColorMode.hsv:
                np.fmod(data, 1.0, where=self._where_hue[0:(end - start) * 3], out=data)
                data = data * 255.0
            else:
                data = data * 255.0
                data = np.clip(data, 0.0, 255.0)
            data = data.astype(np.uint8)
            packet = (b'\x00'
                      + (b'\x02' if color_mode == animfunctions.ColorMode.hsv else b'\x01')
                      + int((end - start) * 3 + 13).to_bytes(2, 'big')
                      + correction.to_bytes(3, 'big')
                      + int(saturation * 255).to_bytes(1, 'big')
                      + int(brightness * 255).to_bytes(1, 'big')
                      + start.to_bytes(2, 'big')
                      + end.to_bytes(2, 'big')
                      + data.tobytes())
            self._send(packet, render_mode, render_target)
            self._send(b'\x00\x03\x00\x05\x00', render_mode, render_target)

    def show_calibration_color(self, count, correction, brightness,
                               render_mode, render_target):
        if render_mode == TargetMode.local:
            if driver.is_raspberrypi():
                driver.ws2811_rgb_render_calibration(self._leds,
                                                     self._channel, self._count,
                                                     correction, brightness)
        else:
            packet = (b'\x00\x00\x00\x08'
                      + correction.to_bytes(3, 'big')
                      + int(brightness * 255).to_bytes(1, 'big'))
            self._send(packet, render_mode, render_target)

    def render(self):
        # send global render command if output mode is raspberry pi
        if driver.is_raspberrypi():
            driver.ws2811_render(self._leds)

    def _send(self, packet, mode, target):
        try:
            if mode == TargetMode.serial:
                if target not in self._targets_serial:
                    self._targets_serial[target] = serial.Serial(target,
                                                                 115200,
                                                                 timeout=0.01,
                                                                 write_timeout=0)
                self._targets_serial[target].write(packet)
            elif mode == TargetMode.udp:
                if target not in self._targets_udp:
                    self._targets_udp[target] = (socket.gethostbyname(target), 8888)
                self._udp_socket.sendto(packet, self._targets_udp[target])
        except Exception as e:
            msg = traceback.format_exception(type(e), e, e.__traceback__)
            print(f'Error during remote rendering: {msg}')

    def set_pixel_rgbw(self, index, r, g, b, w=0, render=True):
        """
        Setzt einen einzelnen Pixel (RGB oder RGBW) unmittelbar.
        r,g,b,w: 0..255
        Wenn das Strip kein W-Kanal hat, wird w ignoriert.
        Bei render=True wird direkt ws2811_render() aufgerufen.
        """
        if not (0 <= index < self._count):
            return False
        if driver.is_raspberrypi():
            # Weißkanal nur wenn vorhanden
            if not self._has_white:
                w = 0
            color = driver.pack_rgbw(r & 0xFF, g & 0xFF, b & 0xFF, w & 0xFF)
            driver.ws2811_led_set(self._channel, index, color)
            if render:
                driver.ws2811_render(self._leds)
            return True
        else:
            # Fallback: über bestehende set_range (normalisiert 0..1)
            self.set_range(
                [(r/255.0, g/255.0, b/255.0)],  # ein Pixel
                index,
                index + 1,
                0xFFFFFF,        # keine Korrekturänderung
                1.0,             # Sättigung
                1.0,             # Helligkeit
                animfunctions.ColorMode.rgb,
                TargetMode.local,
                ''
            )
            return True

    def set_pixels_from_flat(self, data, start=0, render=True):
        """
        Setzt mehrere Pixel aus einem flachen Array.
        Erwartetes Format:
          - Bei Streifen mit White-Kanal: R1,G1,B1,W1,R2,G2,B2,W2,...
          - Ohne White-Kanal: R1,G1,B1,R2,G2,B2,...
        Parameter:
          data   : Sequenz (list/tuple/bytes/bytearray) von ints 0..255
          start  : Startpixel (0-basiert)
          render : True -> am Ende frame rendern
        Rückgabe:
          Anzahl gesetzter Pixel
        Unvollständige (restliche) Werte am Ende werden ignoriert.
        """
        if start < 0 or start >= self._count:
            return 0
        has_w = self._has_white
        cpl = 4 if has_w else 3
        length = len(data)
        full_pixels = (length // cpl)
        if full_pixels <= 0:
            return 0
        max_pixels = min(full_pixels, self._count - start)

        if driver.is_raspberrypi():
            # Direkt in den Hardware-Puffer schreiben
            for i in range(max_pixels):
                base = i * cpl
                r = data[base] & 0xFF
                g = data[base + 1] & 0xFF
                b = data[base + 2] & 0xFF
                w = data[base + 3] & 0xFF if has_w else 0
                color = driver.pack_rgbw(r, g, b, w if has_w else 0)
                driver.ws2811_led_set(self._channel, start + i, color)
            if render:
                driver.ws2811_render(self._leds)
        else:
            # Fallback: in float-Pixel-Liste umwandeln und einmal set_range
            pixels = []
            for i in range(max_pixels):
                base = i * cpl
                r = data[base] / 255.0
                g = data[base + 1] / 255.0
                b = data[base + 2] / 255.0
                pixels.append((r, g, b))
            # Korrektur/Sättigung/Helligkeit neutral halten
            self.set_range(pixels,
                           start,
                           start + max_pixels,
                           0xFFFFFF,
                           1.0,
                           1.0,
                           animfunctions.ColorMode.rgb,
                           TargetMode.local,
                           '')
            if render:
                self.render()
        return max_pixels
