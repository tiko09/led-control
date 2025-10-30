# led-control WS2812B LED Controller Server
# Copyright 2022 jackw01. Released under the MIT License (see LICENSE for details).

import json
import atexit
import shutil
import traceback
from threading import Timer
from pathlib import Path
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
from ledcontrol.animationcontroller import AnimationController
from ledcontrol.ledcontroller import LEDController
from ledcontrol.homekit import homekit_start
from ledcontrol.artnet_server import ArtNetServer
from ledcontrol.led_visualizer import LEDVisualizer
from ledcontrol.pi_discovery import PiDiscoveryService
from ledcontrol.version import get_version_string, get_version_info

import ledcontrol.pixelmappings as pixelmappings
import ledcontrol.animationfunctions as animfunctions
import ledcontrol.colorpalettes as colorpalettes
import ledcontrol.utils as utils
import requests

import logging
logging.basicConfig(level=logging.INFO)

def create_app(led_count,
               config_file,
               pixel_mapping_file,
               refresh_rate,
               led_pin,
               led_data_rate,
               led_dma_channel,
               led_pixel_order,
               led_brightness_limit,
               save_interval,
               enable_hap,
               no_timer_reset,
               dev,
               port=80):
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'led-control-secret-key-change-in-production'
    
    # Initialize SocketIO for LED visualizer
    socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

    # Create pixel mapping function
    if pixel_mapping_file is not None:
        pixel_mapping = json.load(pixel_mapping_file)
        pixel_mapping_file.close()
        led_count = len(pixel_mapping)
        app.logger.info(f'Using pixel mapping from file ({led_count} LEDs)')
        mapping_func = pixelmappings.from_array(pixel_mapping)
    else:
        app.logger.info(f'Using default linear pixel mapping ({led_count} LEDs)')
        mapping_func = pixelmappings.line(led_count)

    leds = LEDController(led_count,
                         led_pin,
                         led_data_rate,
                         led_dma_channel,
                         led_pixel_order)
    
    controller = AnimationController(leds,
                                     refresh_rate,
                                     led_count,
                                     mapping_func,
                                     no_timer_reset,
                                     led_brightness_limit)
    
    # Initialize LED visualizer for real-time browser display
    visualizer = LEDVisualizer(socketio, target_fps=30)
    controller.set_visualizer(visualizer)

    presets = {}
    functions = dict(animfunctions.default)

    # Create file if it doesn't exist already
    if config_file is not None:
        filename = Path(config_file)
    else:
        if dev:
            # In dev mode, use local config file in current directory
            filename = Path.cwd() / 'ledcontrol-dev.json'
            app.logger.info(f'Dev mode: Using config file at {filename}')
        else:
            # In production mode, use /etc
            filename = Path('/etc') / 'ledcontrol.json'
    filename.touch(exist_ok=True)

    # Init controller params and custom animations from settings file
    with filename.open('r') as data_file:
        try:
            settings_str = data_file.read()
            # Apply updates to old versions of settings file
            settings_str = settings_str.replace('master_', '')
            settings_str = settings_str.replace('pattern(t, dt, x, y, prev_state)',
                                                'pattern(t, dt, x, y, z, prev_state)')
            settings = json.loads(settings_str)

            if 'save_version' not in settings:
                app.logger.warning(f'Detected an old save file version at {filename}. Making a backup to {filename}.bak.')
                shutil.copyfile(filename, filename.with_suffix('.json.bak'))

                # Rename 'params' and recreate as 'settings'
                params = settings.pop('params')
                settings['settings'] = {
                    'global_brightness': params['brightness'],
                    'global_color_temp': params['color_temp'],
                    'global_color_r': 1.0,
                    'global_color_g': 1.0,
                    'global_color_b': 1.0,
                    'global_saturation': params['saturation'],
                    'groups': {
                        'main': {
                            'range_start': 0,
                            'range_end': 100000,
                            'render_mode': 'local',
                            'render_target': '',
                            'mapping': [],
                            'name': 'main',
                            'brightness': 1.0,
                            'color_temp': 6500,
                            'saturation': 1.0,
                            'function': 0,
                            'speed': params['primary_speed'],
                            'scale': params['primary_scale'],
                            'palette': 0,
                        }
                    }
                }

                # Add default flag to animation patterns
                for k in settings['patterns']:
                    if 'source' in settings['patterns'][k]:
                        settings['patterns'][k]['default'] = False
                    else:
                        settings['patterns'][k]['default'] = True

                # Rename 'patterns'
                settings['functions'] = settings.pop('patterns')

                # Add default flag to palettes
                for k in settings['palettes']:
                    settings['palettes'][k]['default'] = False

                app.logger.info('Successfully upgraded save file.')

            # Enforce calibration off when starting up
            settings['settings']['calibration'] = 0

            # Set controller settings, (automatically) recalculate things that depend on them
            controller.update_settings(settings['settings'])

            # Read presets
            if 'presets' in settings:
                presets.update(settings['presets'])

            # Read custom animations and changed params for default animations
            for k, v in settings['functions'].items():
                if v['default'] == False:
                    functions[int(k)] = v
                    controller.set_pattern_function(int(k), v['source'])
                elif int(k) in functions:
                    functions[int(k)].update(v)

            # Read color palettes
            for k, v in settings['palettes'].items():
                controller.set_palette(int(k), v)
            controller.calculate_palette_tables()

            app.logger.info(f'Loaded saved settings from {filename}')

        except Exception as e:
            if settings_str == '':
                app.logger.info(f'Creating new settings file at {filename}.')
            else:
                app.logger.warning(f'Some saved settings at {filename} are out of date or invalid. Making a backup of the old file to {filename}.error and creating a new one with default settings.')
                shutil.copyfile(filename, filename.with_suffix('.json.error'))
            
            # Initialize settings as empty dict when loading fails
            settings = {}

    config_defaults = {
        "enable_artnet": False,
        "artnet_universe": 0,
        "artnet_channel_offset": 0,
        "artnet_group_size": 1,
        "artnet_frame_interpolation": "none",   # vorher: artnet_smoothing
        "artnet_frame_interp_size": 2,          # vorher: artnet_filter_size
        "artnet_spatial_smoothing": "none",   # "none", "average", "lerp"
        "artnet_spatial_size": 1,             # Fenstergröße (z.B. 1=aus, 3=3er-Glättung)
        "log_level": "INFO",  # NEU: Logging-Level
    }
    for k, v in config_defaults.items():
        settings.setdefault(k, v)

    # Restore ArtNet parameters from root if present (for backward compatibility)
    if settings_str:  # Only parse if settings_str is not empty
        try:
            root_settings = json.loads(settings_str)
            for k in ("enable_artnet", "artnet_universe", "artnet_channel_offset", "artnet_group_size", "artnet_smoothing", "artnet_filter_size"):
                if k in root_settings:
                    settings[k] = root_settings[k]
                elif k in config_defaults and k not in settings:
                    settings[k] = config_defaults[k]
        except json.JSONDecodeError:
            # If parsing fails, just use defaults
            for k in ("enable_artnet", "artnet_universe", "artnet_channel_offset", "artnet_group_size", "artnet_smoothing", "artnet_filter_size"):
                if k in config_defaults and k not in settings:
                    settings[k] = config_defaults[k]

    artnet_server = None
    
    # Initialize Pi Discovery Service
    discovery_service = None
    pi_master_mode = settings.get('pi_master_mode', False)
    pi_device_name = settings.get('pi_device_name', '')
    pi_group = settings.get('pi_group', '')
    
    def on_device_change(change_type, pi_info):
        """Callback when a Pi is discovered/removed"""
        app.logger.info(f"Pi {change_type}: {pi_info.device_name} ({pi_info.primary_address})")
        
        # Notify connected clients via WebSocket
        if socketio:
            socketio.emit('pi_discovered' if change_type == 'added' else 'pi_removed', 
                         pi_info.to_dict(), 
                         namespace='/discovery')
    
    def start_discovery_service():
        """Start the Pi discovery service"""
        nonlocal discovery_service
        if discovery_service:
            discovery_service.stop()
        
        # Get port from create_app parameter
        import socket
        
        # If device name is empty, use hostname
        device_name = pi_device_name or socket.gethostname()
        
        # Get Git version info
        version_string = get_version_string()
        
        app.logger.info(f"Starting Pi Discovery Service: {device_name} (port {port}, group: '{pi_group}', version: {version_string})")
        
        try:
            discovery_service = PiDiscoveryService(
                port=port,
                device_name=device_name,
                group=pi_group,
                version=version_string,
                on_device_change=on_device_change
            )
            discovery_service.start()
            app.logger.info("Pi Discovery Service started successfully")
        except Exception as e:
            app.logger.error(f"Failed to start Pi Discovery Service: {e}", exc_info=True)
            discovery_service = None
    
    # Start discovery service
    start_discovery_service()
    atexit.register(lambda: discovery_service.stop() if discovery_service else None)

    def set_led(data: bytes, index: int):
        """Set LED data from ArtNet Server and notify visualizer"""
        leds.set_pixels_from_flat(data, index)
        
        # Send to visualizer if connected and ArtNet is active
        if visualizer and artnet_server:
            # ArtNet data format depends on LED pixel order configuration
            # Convert RGBW to RGB by adding white channel to each color
            channels_per_led = leds.getNrOfChannelsPerLed()
            
            if channels_per_led == 4:
                # RGBW: Add W to R, G, B to show true brightness
                # Normalize to 0-1 range for visualizer (it will scale to 0-255)
                rgb_data = []
                for i in range(0, min(len(data), led_count * 4), 4):
                    r, g, b, w = data[i], data[i+1], data[i+2], data[i+3]
                    # Add white to each color channel, clamp to 255, then normalize to 0-1
                    rgb_data.append((
                        min(255, r + w) / 255.0,
                        min(255, g + w) / 255.0,
                        min(255, b + w) / 255.0
                    ))
                visualizer.update_pixels(rgb_data, led_count, 'rgb')
            else:
                # RGB or other format: normalize to 0-1 range
                rgb_data = []
                for i in range(0, min(len(data), led_count * 3), 3):
                    rgb_data.append((
                        data[i] / 255.0,
                        data[i+1] / 255.0,
                        data[i+2] / 255.0
                    ))
                visualizer.update_pixels(rgb_data, led_count, 'rgb')

    def stop_current_animation():
        controller.end_animation()
        controller.clear_leds()
        app.logger.debug("Animation gestoppt (ArtNet aktiv)")

    @app.route('/')
    def index():
        'Returns web app page'
        return app.send_static_file('index.html')

    @app.get('/getsettings')
    def get_settings():
        'Get settings'
        return jsonify(controller.get_settings())

    @app.post('/updatesettings')
    def update_settings():
        'Update settings'
        new_settings = request.json
        controller.update_settings(new_settings)
        return jsonify(result='')

    @app.get('/getpresets')
    def get_presets():
        'Get presets'
        return jsonify(presets)

    @app.post('/updatepreset')
    def update_preset():
        'Update a preset'
        presets[request.json['key']] = request.json['value']
        return jsonify(result='')

    @app.post('/removepreset')
    def remove_preset():
        'Remove a preset'
        del presets[request.json['key']]
        return jsonify(result='')

    @app.post('/removegroup')
    def remove_group():
        'Remove a group'
        controller.delete_group(request.json['key'])
        return jsonify(result='')

    @app.get('/getfunctions')
    def get_functions():
        'Get functions'
        return jsonify(functions)

    @app.post('/compilefunction')
    def compile_function():
        'Compiles a function, returns errors and warnings in JSON array form'
        key = request.json['key']
        errors, warnings = controller.set_pattern_function(key, functions[key]['source'])
        return jsonify(errors=errors, warnings=warnings)

    @app.post('/updatefunction')
    def update_function():
        'Update a function'
        functions[request.json['key']] = request.json['value']
        return jsonify(result='')

    @app.post('/removefunction')
    def remove_function():
        'Remove a function'
        del functions[request.json['key']]
        return jsonify(result='')

    @app.get('/getpalettes')
    def get_palettes():
        'Get palettes'
        return jsonify(controller.get_palettes())

    @app.post('/updatepalette')
    def update_palette():
        'Update a palette'
        controller.set_palette(request.json['key'], request.json['value'])
        controller.calculate_palette_table(request.json['key'])
        return jsonify(result='')

    @app.post('/removepalette')
    def remove_palette():
        'Remove a palette'
        controller.delete_palette(request.json['key'])
        return jsonify(result='')

    @app.get('/getfps')
    def get_fps():
        'Returns latest animation frames per second'
        return jsonify(fps=controller.get_frame_rate())
    
    @app.get('/getversion')
    def get_version():
        'Returns Git version information'
        return jsonify(get_version_info())

    @app.get('/resettimer')
    def reset_timer():
        'Resets animation timer'
        controller.reset_timer()
        return jsonify(result='')

    def save_settings():
        'Save controller settings, patterns, and palettes'
        functions_2 = {}
        for k, v in functions.items():
            if not v['default']:
                functions_2[str(k)] = v
            else:
                functions_2[str(k)] = {n: v[n] for n in ('default', 'primary_speed', 'primary_scale')}

        palettes_2 = {str(k): v for (k, v) in controller.get_palettes().items() if not v['default']}

        data = {
            'save_version': 2,
            'settings': controller.get_settings(),
            'presets': presets,
            'functions': functions_2,
            'palettes': palettes_2,
        }
        data.update({
            "enable_artnet": settings["enable_artnet"],
            "artnet_universe": settings["artnet_universe"],
            "artnet_channel_offset": settings["artnet_channel_offset"],
            "artnet_group_size": settings.get("artnet_group_size", 1),
            "pi_device_name": settings.get("pi_device_name", ""),
            "pi_group": settings.get("pi_group", ""),
            "pi_master_mode": settings.get("pi_master_mode", False),
        })
        try:
            with filename.open('w') as data_file:
                json.dump(data, data_file, sort_keys=True, indent=4)
                app.logger.info(f'Saved settings to {filename}')
        except PermissionError:
            app.logger.error(f'No permission to write to {filename}')
            app.logger.error('Hint: Use --config_file to specify a writable location, or run in dev mode (--dev)')
        except Exception as e:
            app.logger.error(f'Could not save settings to {filename}: {e}', exc_info=True)

    def auto_save_settings():
        'Timer for automatically saving settings'
        save_settings()
        t = Timer(save_interval, auto_save_settings)
        t.daemon = True
        t.start()

    controller.begin_animation_thread()
    atexit.register(save_settings)
    atexit.register(controller.clear_leds)
    atexit.register(controller.end_animation)
    auto_save_settings()

    if enable_hap:
        def setter_callback(char_values):
            new_settings = {}
            if 'On' in char_values:
                new_settings['on'] = char_values['On']
            if 'Brightness' in char_values:
                new_settings['global_brightness'] = char_values['Brightness'] / 100.0
            if 'Saturation' in char_values:
                new_settings['global_saturation'] = char_values['Saturation'] / 100.0
            controller.update_settings(new_settings)

        hap_accessory = homekit_start(setter_callback)
        hap_accessory.on.set_value(controller.get_settings()['on'])
        hap_accessory.brightness.set_value(controller.get_settings()['global_brightness'] * 100.0)
        hap_accessory.saturation.set_value(controller.get_settings()['global_saturation'] * 100.0)

    # Beim Start ArtNet (Warnung Kapazität):
    if settings.get("enable_artnet"):
        stop_current_animation()
        max_leds_universe = (512 - settings.get("artnet_channel_offset", 0)) // leds.getNrOfChannelsPerLed()
        if led_count > max_leds_universe:
            app.logger.warning(
                "LED count (%d) > DMX Universe Kapazität (%d) -> Rest ignoriert",
                led_count, max_leds_universe
            )
        artnet_server = ArtNetServer(
            set_led_rgbw=set_led,
            led_count=led_count,
            universe=settings.get("artnet_universe", 0),
            channel_offset=settings.get("artnet_channel_offset", 0),
            channels_per_led=leds.getNrOfChannelsPerLed(),
            group_size=settings.get("artnet_group_size", 1),
            frame_interpolation=settings.get("artnet_frame_interpolation", "none"),
            frame_interp_size=settings.get("artnet_frame_interp_size", 2),
            spatial_smoothing=settings.get("artnet_spatial_smoothing", "none"),
            spatial_size=settings.get("artnet_spatial_size", 1),
        )
        artnet_server.start()
        app.logger.debug(
            "ArtNetServer aktiv: universe=%d offset=%d cpl=%d max_leds_universe=%d",
            settings["artnet_universe"],
            settings["artnet_channel_offset"],
            leds.getNrOfChannelsPerLed(),
            (512 - settings["artnet_channel_offset"]) // leds.getNrOfChannelsPerLed()
        )

    # ArtNet POST (Kapazität prüfen nach Änderung):
    @app.post("/api/artnet")
    def api_set_artnet():
        nonlocal artnet_server
        data = request.get_json(force=True)
        settings["enable_artnet"] = bool(data.get("enable_artnet"))
        settings["artnet_universe"] = int(data.get("artnet_universe", 0))
        settings["artnet_channel_offset"] = int(data.get("artnet_channel_offset", 0))
        settings["artnet_group_size"] = max(1, int(data.get("artnet_group_size", 1)))
        settings["artnet_frame_interpolation"] = data.get("artnet_frame_interpolation", "none")
        settings["artnet_frame_interp_size"] = max(1, int(data.get("artnet_frame_interp_size", 2)))
        settings["artnet_spatial_smoothing"] = data.get("artnet_spatial_smoothing", "none")
        settings["artnet_spatial_size"] = max(1, int(data.get("artnet_spatial_size", 1)))

        if artnet_server:
            app.logger.debug("Stoppe ArtNetServer für Neustart")
            artnet_server.stop()
            artnet_server = None

        if settings["enable_artnet"]:
            stop_current_animation()
            group_size = settings["artnet_group_size"]
            max_dmx_pixels = (512 - settings["artnet_channel_offset"]) // leds.getNrOfChannelsPerLed()
            max_phys_leds = max_dmx_pixels * group_size
            if led_count > max_phys_leds:
                app.logger.warning(
                    "LED count (%d) > physikalische Kapazität (%d) (Universe=%d offset=%d group=%d)",
                    led_count, max_phys_leds,
                    settings["artnet_universe"],
                    settings["artnet_channel_offset"],
                    group_size
                )
            artnet_server = ArtNetServer(
                set_led_rgbw=set_led,
                led_count=led_count,
                universe=settings["artnet_universe"],
                channel_offset=settings["artnet_channel_offset"],
                channels_per_led=leds.getNrOfChannelsPerLed(),
                group_size=group_size,
                frame_interpolation=settings["artnet_frame_interpolation"],  # neu
                frame_interp_size=settings["artnet_frame_interp_size"],      # neu
                spatial_smoothing=settings["artnet_spatial_smoothing"],
                spatial_size=settings["artnet_spatial_size"],
            )
            artnet_server.start()
        else:
            app.logger.debug("ArtNet deaktiviert")
            controller.clear_leds()
            # Only start animation thread if not already running
            if not controller.is_animation_running():
                app.logger.debug("Starte Animation Thread")
                controller.begin_animation_thread()
            else:
                app.logger.debug("Animation Thread läuft bereits")
        save_settings()
        return {"status": "ok"}

    @app.get("/api/artnet")
    def api_get_artnet():
        return {
            "enable_artnet": settings.get("enable_artnet", False),
            "artnet_universe": settings.get("artnet_universe", 0),
            "artnet_channel_offset": settings.get("artnet_channel_offset", 0),
            "artnet_group_size": settings.get("artnet_group_size", 1),
            "artnet_frame_interpolation": settings.get("artnet_frame_interpolation", "none"),
            "artnet_frame_interp_size": settings.get("artnet_frame_interp_size", 2),
            "artnet_spatial_smoothing": settings.get("artnet_spatial_smoothing", "none"),
            "artnet_spatial_size": settings.get("artnet_spatial_size", 1),
        }

    # Logging-Level setzen (Hilfsfunktion)
    def set_log_level(level):
        import logging
        lvl = getattr(logging, level.upper(), logging.INFO)
        logging.getLogger().setLevel(lvl)
        # Optional: auch ArtNet-Logger etc.
        logging.getLogger("artnet").setLevel(lvl)

    set_log_level(settings.get("log_level", "INFO"))

    @app.get("/api/loglevel")
    def api_get_loglevel():
        return {"log_level": settings.get("log_level", "INFO")}

    @app.post("/api/loglevel")
    def api_set_loglevel():
        data = request.get_json(force=True)
        level = data.get("log_level", "INFO")
        settings["log_level"] = level
        set_log_level(level)
        return {"status": "ok"}
    
    # ============================================================================
    # Pi Discovery & Sync API Endpoints
    # ============================================================================
    
    @app.get("/api/pi/info")
    def api_get_pi_info():
        """Get information about this Pi"""
        import socket
        hostname = socket.gethostname()
        version_info = get_version_info()
        
        return {
            "device_name": pi_device_name or hostname,
            "hostname": hostname,
            "group": pi_group,
            "master_mode": pi_master_mode,
            "version": version_info['version_string'],
            "version_details": {
                "commit": version_info['commit'],
                "branch": version_info['branch'],
                "tag": version_info['tag'],
            },
            "led_count": led_count,
        }
    
    @app.get("/api/pi/state")
    def api_get_pi_state():
        """Get current animation state (for syncing to other Pis)"""
        current_settings = controller.get_settings()
        
        # Get the main group's settings (or first group)
        groups = current_settings.get('groups', {})
        main_group = groups.get('main', next(iter(groups.values()), {}))
        
        return {
            "device_name": pi_device_name,
            "group": pi_group,
            "settings": {
                "global_brightness": current_settings.get('global_brightness', 1.0),
                "global_color_temp": current_settings.get('global_color_temp', 6500),
                "global_saturation": current_settings.get('global_saturation', 1.0),
                "on": current_settings.get('on', True),
            },
            "animation": {
                "function": main_group.get('function', 0),
                "speed": main_group.get('speed', 1.0),
                "scale": main_group.get('scale', 1.0),
                "palette": main_group.get('palette', 0),
            }
        }
    
    @app.post("/api/pi/sync")
    def api_sync_from_pi():
        """Receive sync data from another Pi"""
        data = request.get_json(force=True)
        
        source_device = data.get('device_name', 'Unknown')
        app.logger.info(f"Receiving sync from {source_device}")
        
        # Extract sync data
        sync_settings = data.get('settings', {})
        sync_animation = data.get('animation', {})
        
        # Apply global settings if provided
        if sync_settings:
            new_settings = {}
            if 'global_brightness' in sync_settings:
                new_settings['global_brightness'] = sync_settings['global_brightness']
            if 'global_color_temp' in sync_settings:
                new_settings['global_color_temp'] = sync_settings['global_color_temp']
            if 'global_saturation' in sync_settings:
                new_settings['global_saturation'] = sync_settings['global_saturation']
            if 'on' in sync_settings:
                new_settings['on'] = sync_settings['on']
            
            if new_settings:
                controller.update_settings(new_settings)
        
        # Apply animation settings if provided
        if sync_animation:
            current_settings = controller.get_settings()
            groups = current_settings.get('groups', {})
            main_group_key = 'main' if 'main' in groups else next(iter(groups.keys()), None)
            
            if main_group_key:
                new_group_settings = {}
                if 'function' in sync_animation:
                    new_group_settings['function'] = sync_animation['function']
                if 'speed' in sync_animation:
                    new_group_settings['speed'] = sync_animation['speed']
                if 'scale' in sync_animation:
                    new_group_settings['scale'] = sync_animation['scale']
                if 'palette' in sync_animation:
                    new_group_settings['palette'] = sync_animation['palette']
                
                if new_group_settings:
                    controller.update_group(main_group_key, new_group_settings)
        
        app.logger.info(f"Sync from {source_device} applied successfully")
        return {"status": "ok", "message": "Sync applied"}
    
    @app.get("/api/pi/discover")
    def api_get_discovered_pis():
        """Get list of all discovered Pis on the network"""
        if not discovery_service:
            return {"devices": []}
        
        devices = discovery_service.get_devices()
        return {
            "devices": [pi.to_dict() for pi in devices],
            "count": len(devices)
        }
    
    @app.post("/api/pi/settings")
    def api_update_pi_settings():
        """Update Pi discovery settings (device name, group, master mode)"""
        nonlocal pi_device_name, pi_group, pi_master_mode
        
        data = request.get_json(force=True)
        
        if 'device_name' in data:
            pi_device_name = data['device_name']
            settings['pi_device_name'] = pi_device_name
        
        if 'group' in data:
            pi_group = data['group']
            settings['pi_group'] = pi_group
        
        if 'master_mode' in data:
            pi_master_mode = bool(data['master_mode'])
            settings['pi_master_mode'] = pi_master_mode
        
        # Update discovery service with new info
        if discovery_service:
            discovery_service.update_device_info(
                device_name=pi_device_name,
                group=pi_group
            )
        
        save_settings()
        app.logger.info(f"Pi settings updated: {pi_device_name} / {pi_group} / Master: {pi_master_mode}")
        
        return {"status": "ok"}
    
    @app.get("/api/pi/settings")
    def api_get_pi_settings():
        """Get Pi discovery settings"""
        return {
            "device_name": pi_device_name,
            "group": pi_group,
            "master_mode": pi_master_mode,
        }
    
    @app.post("/api/pi/sync-to")
    def api_sync_to_pi():
        """Send current state to another Pi"""
        data = request.get_json(force=True)
        target_url = data.get('url')
        
        if not target_url:
            return {"status": "error", "message": "No target URL provided"}, 400
        
        # Get current state
        current_state = api_get_pi_state()
        
        try:
            # Send to target Pi
            response = requests.post(
                f"{target_url}/api/pi/sync",
                json=current_state,
                timeout=5
            )
            
            if response.status_code == 200:
                app.logger.info(f"Successfully synced to {target_url}")
                return {"status": "ok", "message": "Sync sent successfully"}
            else:
                app.logger.error(f"Failed to sync to {target_url}: {response.status_code}")
                return {"status": "error", "message": f"Target returned {response.status_code}"}, 500
                
        except requests.exceptions.RequestException as e:
            app.logger.error(f"Failed to sync to {target_url}: {e}")
            return {"status": "error", "message": str(e)}, 500
    
    @app.post("/api/pi/sync-all")
    def api_sync_to_all():
        """Send current state to all discovered Pis (or specific group)"""
        data = request.get_json(force=True)
        target_group = data.get('group', None)  # None = all groups
        
        if not discovery_service:
            return {"status": "error", "message": "Discovery service not available"}, 500
        
        devices = discovery_service.get_devices()
        
        # Filter by group if specified
        if target_group:
            devices = [pi for pi in devices if pi.group == target_group]
        
        # Get current state
        current_state = api_get_pi_state()
        
        success_count = 0
        failed = []
        
        for pi in devices:
            try:
                response = requests.post(
                    f"{pi.url}/api/pi/sync",
                    json=current_state,
                    timeout=5
                )
                
                if response.status_code == 200:
                    success_count += 1
                    app.logger.info(f"Synced to {pi.device_name}")
                else:
                    failed.append(pi.device_name)
                    app.logger.error(f"Failed to sync to {pi.device_name}: {response.status_code}")
                    
            except requests.exceptions.RequestException as e:
                failed.append(pi.device_name)
                app.logger.error(f"Failed to sync to {pi.device_name}: {e}")
        
        return {
            "status": "ok",
            "synced": success_count,
            "failed": len(failed),
            "failed_devices": failed,
            "total": len(devices)
        }
    
    # WebSocket handlers for LED visualizer
    @socketio.on('connect', namespace='/visualizer')
    def visualizer_connect():
        visualizer.on_connect()
        emit('connected', {'led_count': led_count, 'fps': visualizer.target_fps})
    
    @socketio.on('disconnect', namespace='/visualizer')
    def visualizer_disconnect():
        visualizer.on_disconnect()
    
    @socketio.on('get_stats', namespace='/visualizer')
    def visualizer_get_stats():
        return visualizer.get_stats()
    
    # WebSocket handlers for Pi discovery
    @socketio.on('connect', namespace='/discovery')
    def discovery_connect():
        """Send initial list of discovered Pis when client connects"""
        if discovery_service:
            devices = discovery_service.get_devices()
            emit('devices_list', {
                'devices': [pi.to_dict() for pi in devices]
            })
    
    @socketio.on('disconnect', namespace='/discovery')
    def discovery_disconnect():
        pass
    
    @socketio.on('request_devices', namespace='/discovery')
    def discovery_request_devices():
        """Client can request updated device list"""
        if discovery_service:
            devices = discovery_service.get_devices()
            emit('devices_list', {
                'devices': [pi.to_dict() for pi in devices]
            })
    
    # Store socketio instance in app for access from main
    app.socketio = socketio

    return app
