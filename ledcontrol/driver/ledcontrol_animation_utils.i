/* led-control WS2812B LED Controller Server
 * Copyright 2021 jackw01. Released under the MIT License (see LICENSE for details).
 *
 * SWIG interface for animation utility functions (performance-critical)
 * This provides C implementations of animation functions for better performance
 * while the LED driver itself uses rpi5-ws2812
 */

%module ledcontrol_animation_utils

%{
#include "animation_utils.h"
#include "led_render.h"
#include "color_types.h"
%}

/* Include standard integer types */
%include "stdint.i"

/* Parse the header files to generate wrappers */
%include "color_types.h"
%include "animation_utils.h"

/* Only include the utility functions from led_render.h, not LED-specific stuff */
float clamp(float d, float min, float max);

typedef struct color_rgb_float {
  float r;
  float g;
  float b;
} color_rgb_float;

color_rgb_float blackbody_to_rgb(float kelvin);
color_rgb_float blackbody_correction_rgb(color_rgb_float rgb, float kelvin);
