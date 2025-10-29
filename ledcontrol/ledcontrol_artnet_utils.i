/* led-control WS2812B LED Controller Server
 * Copyright 2021 jackw01. Released under the MIT License (see LICENSE for details).
 *
 * SWIG interface for ArtNet spatial smoothing (performance-critical)
 * Provides high-performance spatial filtering for LED data
 */

%module ledcontrol_artnet_utils

%{
#include <math.h>
#include <stdint.h>
#include <string.h>
#include <stdlib.h>

/* Spatial smoothing with configurable kernel
 * 
 * input: Input LED data (RGBW bytes, 4 bytes per LED)
 * output: Output LED data buffer (must be pre-allocated)
 * n_leds: Number of LEDs
 * window: Kernel window size (will be made odd if even)
 * smoothing_type: 0=average, 1=linear, 2=gaussian
 */
void spatial_smooth_rgbw(const uint8_t* input, uint8_t* output, int n_leds, int window, int smoothing_type) {
    if (n_leds <= 0 || window <= 1) {
        // No smoothing, just copy
        memcpy(output, input, n_leds * 4);
        return;
    }
    
    // Make window odd
    if (window % 2 == 0) {
        window += 1;
    }
    
    int half = window / 2;
    float* kernel = (float*)malloc(window * sizeof(float));
    
    // Build kernel based on type
    if (smoothing_type == 0) {
        // Average
        float val = 1.0f / window;
        for (int i = 0; i < window; i++) {
            kernel[i] = val;
        }
    } else if (smoothing_type == 1) {
        // Linear (triangle)
        int center = window / 2;
        float kernel_sum = 0.0f;
        for (int i = 0; i < window; i++) {
            int dist = abs(i - center);
            kernel[i] = (float)(window - dist);
            kernel_sum += kernel[i];
        }
        // Normalize
        for (int i = 0; i < window; i++) {
            kernel[i] /= kernel_sum;
        }
    } else if (smoothing_type == 2) {
        // Gaussian
        int center = window / 2;
        float sigma = fmaxf(1.0f, window / 4.0f);
        float kernel_sum = 0.0f;
        for (int i = 0; i < window; i++) {
            float dist = (float)(i - center);
            kernel[i] = expf(-0.5f * (dist / sigma) * (dist / sigma));
            kernel_sum += kernel[i];
        }
        // Normalize
        for (int i = 0; i < window; i++) {
            kernel[i] /= kernel_sum;
        }
    } else {
        // Default to average
        float val = 1.0f / window;
        for (int i = 0; i < window; i++) {
            kernel[i] = val;
        }
    }
    
    // Apply kernel to each LED
    for (int i = 0; i < n_leds; i++) {
        float acc[4] = {0.0f, 0.0f, 0.0f, 0.0f};
        
        // Convolve with kernel
        for (int k = 0; k < window; k++) {
            int neighbor_idx = i + (k - half);
            
            // Clamp to valid range
            if (neighbor_idx >= 0 && neighbor_idx < n_leds) {
                int base = neighbor_idx * 4;
                float weight = kernel[k];
                
                acc[0] += input[base + 0] * weight;
                acc[1] += input[base + 1] * weight;
                acc[2] += input[base + 2] * weight;
                acc[3] += input[base + 3] * weight;
            }
        }
        
        // Write output
        int out_base = i * 4;
        output[out_base + 0] = (uint8_t)(acc[0] + 0.5f);  // Round
        output[out_base + 1] = (uint8_t)(acc[1] + 0.5f);
        output[out_base + 2] = (uint8_t)(acc[2] + 0.5f);
        output[out_base + 3] = (uint8_t)(acc[3] + 0.5f);
    }
    
    free(kernel);
}

/* Frame interpolation with history
 * 
 * current: Current frame data (RGBW bytes)
 * history: Array of previous frames (flattened: n_leds * history_size * 4 bytes)
 * output: Output buffer
 * n_leds: Number of LEDs
 * history_size: Number of frames to average/interpolate
 * interp_type: 0=none, 1=average, 2=lerp
 */
void frame_interpolate_rgbw(const uint8_t* current, const uint8_t* history, 
                            uint8_t* output, int n_leds, int history_size, int interp_type) {
    if (interp_type == 0 || history_size <= 1) {
        // No interpolation, just copy current
        memcpy(output, current, n_leds * 4);
        return;
    }
    
    for (int i = 0; i < n_leds; i++) {
        int base = i * 4;
        
        if (interp_type == 1) {
            // Average over history
            float acc[4] = {0.0f, 0.0f, 0.0f, 0.0f};
            
            // Add current frame
            acc[0] += current[base + 0];
            acc[1] += current[base + 1];
            acc[2] += current[base + 2];
            acc[3] += current[base + 3];
            
            // Add history frames
            for (int h = 0; h < history_size - 1; h++) {
                int hist_base = (h * n_leds + i) * 4;
                acc[0] += history[hist_base + 0];
                acc[1] += history[hist_base + 1];
                acc[2] += history[hist_base + 2];
                acc[3] += history[hist_base + 3];
            }
            
            // Average
            float divisor = (float)history_size;
            output[base + 0] = (uint8_t)(acc[0] / divisor + 0.5f);
            output[base + 1] = (uint8_t)(acc[1] / divisor + 0.5f);
            output[base + 2] = (uint8_t)(acc[2] / divisor + 0.5f);
            output[base + 3] = (uint8_t)(acc[3] / divisor + 0.5f);
            
        } else if (interp_type == 2) {
            // Linear interpolation with most recent history frame
            float alpha = 1.0f / history_size;
            
            // Most recent history frame is at index 0
            float prev_r = history[base + 0];
            float prev_g = history[base + 1];
            float prev_b = history[base + 2];
            float prev_w = history[base + 3];
            
            float curr_r = current[base + 0];
            float curr_g = current[base + 1];
            float curr_b = current[base + 2];
            float curr_w = current[base + 3];
            
            output[base + 0] = (uint8_t)(prev_r + alpha * (curr_r - prev_r) + 0.5f);
            output[base + 1] = (uint8_t)(prev_g + alpha * (curr_g - prev_g) + 0.5f);
            output[base + 2] = (uint8_t)(prev_b + alpha * (curr_b - prev_b) + 0.5f);
            output[base + 3] = (uint8_t)(prev_w + alpha * (curr_w - prev_w) + 0.5f);
        }
    }
}
%}

/* SWIG typemaps for byte arrays */
%include "pybuffer.i"

/* Input buffer (read-only) */
%pybuffer_binary(const uint8_t* input, int input_len);

/* Output buffer (writable) - caller must allocate */
%pybuffer_mutable_binary(uint8_t* output, int output_len);

/* History buffer for frame interpolation */
%pybuffer_binary(const uint8_t* history, int history_len);

/* Function declarations with buffer sizes */
%inline %{
/* Python-friendly wrapper for spatial_smooth_rgbw */
void spatial_smooth_rgbw_py(const uint8_t* input, int input_len,
                            uint8_t* output, int output_len,
                            int n_leds, int window, int smoothing_type) {
    if (input_len < n_leds * 4 || output_len < n_leds * 4) {
        return;  // Buffer too small
    }
    spatial_smooth_rgbw(input, output, n_leds, window, smoothing_type);
}

/* Python-friendly wrapper for frame_interpolate_rgbw */
void frame_interpolate_rgbw_py(const uint8_t* current, int current_len,
                               const uint8_t* history, int history_len,
                               uint8_t* output, int output_len,
                               int n_leds, int history_size, int interp_type) {
    if (current_len < n_leds * 4 || output_len < n_leds * 4) {
        return;  // Buffer too small
    }
    if (history_size > 1 && history_len < n_leds * (history_size - 1) * 4) {
        return;  // History buffer too small
    }
    frame_interpolate_rgbw(current, history, output, n_leds, history_size, interp_type);
}
%}
