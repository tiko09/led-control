# led-control WS2812B LED Controller Server
# Copyright 2022 jackw01. Released under the MIT License (see LICENSE for details).

import argparse
from ledcontrol.app import create_app

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=80,
                        help='Port to use for web interface. Default: 80')
    parser.add_argument('--host', default='0.0.0.0',
                        help='Hostname to use for web interface. Default: 0.0.0.0')
    parser.add_argument('--led_count', type=int, default=0,
                        help='Number of LEDs')
    parser.add_argument('--config_file',
                        help='Location of config file. Default: /etc/ledcontrol.json')
    parser.add_argument('--pixel_mapping_json', type=argparse.FileType('r'),
                        help='JSON file containing pixel mapping (see README)')
    parser.add_argument('--fps', type=int, default=60,
                        help='Refresh rate limit for LEDs, in FPS. Default: 60')
    parser.add_argument('--led_pin', type=int, default=18,
                        help='Pin for LEDs. Default: 18. NOTE: On Raspberry Pi 5, this is ignored - GPIO19 (SPI MOSI) is always used.')
    parser.add_argument('--led_data_rate', type=int, default=800000,
                        help='Data rate for LEDs. Default: 800000 Hz. NOTE: On Raspberry Pi 5, SPI frequency is fixed at 6.5 MHz')
    parser.add_argument('--led_dma_channel', type=int, default=10,
                        help='DMA channel for LEDs. DO NOT USE CHANNEL 5 ON Pi 3 B. Default: 10. NOTE: On Raspberry Pi 5, this is ignored - SPI does not use DMA')
    parser.add_argument('--led_pixel_order', default='GRB',
                        help='LED color channel order. Any combination of RGB with or without a W at the end. Default: GRB, try GRBW for SK6812')
    parser.add_argument('--led_brightness_limit', type=float, default=1.0,
                        help='LED maximum brightness limit for the web UI. Float from 0.0-1.0. Default: 1.0')
    parser.add_argument('--save_interval', type=int, default=60,
                        help='Interval for automatically saving settings in seconds. Default: 60')
    parser.add_argument('--hap', action='store_true',
                        help='Enable HomeKit Accessory Protocol support. Default: False')
    parser.add_argument('--no_timer_reset', action='store_true',
                        help='Do not reset the animation timer when patterns are changed. Default: False')
    parser.add_argument('--dev', action='store_true',
                        help='Development flag. Default: False')
    args = parser.parse_args()

    app = create_app(args.led_count,
                     args.config_file,
                     args.pixel_mapping_json,
                     args.fps,
                     args.led_pin,
                     args.led_data_rate,
                     args.led_dma_channel,
                     args.led_pixel_order.upper(),
                     args.led_brightness_limit,
                     args.save_interval,
                     args.hap,
                     args.no_timer_reset,
                     args.dev,
                     args.port)

    if args.dev:
        # Development mode: use Flask-SocketIO's built-in server
        # Disable auto-reload to prevent settings loss and animation interruption
        app.socketio.run(app, host=args.host, port=args.port, debug=True, use_reloader=False)
    else:
        # Production mode: Try to use eventlet or gevent for WebSocket support
        # Fall back to bjoern if neither is available (but WebSockets won't work)
        try:
            # Try eventlet first (recommended for Flask-SocketIO)
            import eventlet
            eventlet.monkey_patch()
            print(f"Starting server with eventlet (WebSocket support enabled)")
            app.socketio.run(app, host=args.host, port=args.port)
        except ImportError:
            try:
                # Try gevent as fallback
                from gevent import monkey
                monkey.patch_all()
                import gevent.pywsgi
                from geventwebsocket.handler import WebSocketHandler
                print(f"Starting server with gevent (WebSocket support enabled)")
                app.socketio.run(app, host=args.host, port=args.port)
            except ImportError:
                # Fall back to bjoern (no WebSocket support)
                print("Warning: Neither eventlet nor gevent found. WebSocket features will not work.")
                print("Install eventlet for full WebSocket support: pip install eventlet")
                print("LED Visualizer and real-time Discovery updates will not function.")
                try:
                    import bjoern
                    print(f"Starting server with bjoern on {args.host}:{args.port}")
                    bjoern.run(app, host=args.host, port=args.port)
                except ImportError:
                    print("Error: No suitable WSGI server found. Install eventlet or bjoern.")
                    print("Install with: pip install eventlet")
                    import sys
                    sys.exit(1)
