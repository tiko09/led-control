#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys, io, os, subprocess
import shutil
from setuptools import find_packages, setup, Extension
from setuptools.command.build_ext import build_ext as _build_ext

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
                # Pi 3, Pi 4, or older
                return 3
    except Exception:
        pass
    return 0

def is_raspberrypi():
    return get_raspberry_pi_version() > 0

# Custom build_ext to copy .so files to the correct package directories
class build_ext(_build_ext):
    def run(self):
        _build_ext.run(self)
        # Copy .so files to package directories after building
        if self.extensions:
            for ext in self.extensions:
                if ext.name == '_ledcontrol_animation_utils':
                    self._copy_extension_to_package(ext, 'ledcontrol/driver')
                elif ext.name == '_ledcontrol_artnet_utils':
                    self._copy_extension_to_package(ext, 'ledcontrol')
    
    def _copy_extension_to_package(self, ext, package_dir):
        """Copy the built extension to the package directory"""
        ext_path = self.get_ext_fullpath(ext.name)
        if os.path.exists(ext_path):
            # Get just the filename
            ext_filename = os.path.basename(ext_path)
            # Target path in package directory
            target = os.path.join(package_dir, ext_filename)
            # Copy the file
            shutil.copy2(ext_path, target)
            print(f"Copied {ext_filename} to {package_dir}/")
        else:
            print(f"Warning: Extension {ext.name} not found at {ext_path}")

# Detect Raspberry Pi version for conditional dependencies
pi_version = get_raspberry_pi_version()

# Base requirements for all platforms
requirements = [
    'Flask==2.2.2',
    'flask-socketio>=5.3.0',
    'python-socketio>=5.7.0',
    'RestrictedPython>=5.2',
    'HAP-python==4.4.0',
    'pyopenssl==22.1.0',
    'numpy==1.26.4',
    'pyserial>=3.5',
    'Werkzeug==2.2.2',
    'zeroconf>=0.132.0',
    'requests>=2.28.0',
    'eventlet>=0.33.0',
]

# Add Linux-specific dependencies
if sys.platform.startswith('linux'):
    requirements.append('bjoern>=3.2.1')

# Add Raspberry Pi specific LED drivers
if pi_version == 5:
    # Raspberry Pi 5: Use SPI-based driver
    requirements.append('rpi5-ws2812')
    print("Detected Raspberry Pi 5 - will use rpi5-ws2812 driver (SPI-based)")
elif pi_version == 3:
    # Raspberry Pi 3/4: Use PWM-based driver
    requirements.append('rpi_ws281x')
    print("Detected Raspberry Pi 3/4 - will use rpi_ws281x driver (PWM-based)")
else:
    # Non-Raspberry Pi: Use fast noise library for development
    requirements.append('pyfastnoisesimd>=0.4.2')
    print("Non-Raspberry Pi system detected - using simulation mode")

# SWIG extensions for performance-critical functions
animation_utils_extension = None
artnet_utils_extension = None
rpi_ws281x_extension = None

# Only build extensions if we're on a system with a compiler and SWIG
# The extensions provide better performance but are not required
if sys.platform.startswith('linux'):
    # Check if SWIG is available
    has_swig = False
    try:
        subprocess.check_call(['swig', '-version'], 
                             stdout=subprocess.DEVNULL, 
                             stderr=subprocess.DEVNULL)
        has_swig = True
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    
    if has_swig:
        # Use .i files directly - setuptools will run SWIG automatically
        animation_utils_extension = Extension(
            '_ledcontrol_animation_utils',
            sources=['ledcontrol/driver/ledcontrol_animation_utils.i'],
            include_dirs=['ledcontrol/driver'],
            extra_compile_args=['-O3', '-ffast-math', '-std=c99'],
        )
        artnet_utils_extension = Extension(
            '_ledcontrol_artnet_utils',
            sources=['ledcontrol/ledcontrol_artnet_utils.i'],
            include_dirs=['ledcontrol'],
            extra_compile_args=['-O3', '-std=c99'],
            extra_link_args=['-lm'],
        )
        
        # For Raspberry Pi 3/4: Build custom rpi_ws281x driver wrapper
        if pi_version == 3:
            rpi_ws281x_extension = Extension(
                '_ledcontrol_rpi_ws281x_driver',
                sources=[
                    'ledcontrol/driver/ledcontrol_rpi_ws281x_driver.i',  # SWIG will generate _wrap.c
                    'ledcontrol/driver/rpi_ws281x/ws2811.c',
                    'ledcontrol/driver/rpi_ws281x/pwm.c',
                    'ledcontrol/driver/rpi_ws281x/dma.c',
                    'ledcontrol/driver/rpi_ws281x/pcm.c',
                    'ledcontrol/driver/rpi_ws281x/rpihw.c',
                    'ledcontrol/driver/rpi_ws281x/mailbox.c',
                ],
                include_dirs=[
                    'ledcontrol/driver',
                    'ledcontrol/driver/rpi_ws281x',
                ],
                extra_compile_args=['-O3', '-std=c99'],
                extra_link_args=['-lm'],
                swig_opts=['-I/usr/include'],  # Help SWIG find system headers
            )
            print("Building custom rpi_ws281x driver for Raspberry Pi 3/4")
        
        print("SWIG found - C extensions will be built for maximum performance")
    else:
        print("Warning: SWIG not found. C extensions will not be built.")
        print("Install SWIG with: sudo apt-get install swig")
        print("The software will work with Python fallback implementations.")

setup(
    name='led-control',
    version='2.0.0',
    description='WS2812 LED strip controller with web interface for Raspberry Pi',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    author='jackw01',
    python_requires='>=3.7.0',
    url='https://github.com/jackw01/led-control',
    packages=find_packages(),
    zip_safe=False,
    install_requires=requirements,
    setup_requires=requirements,
    ext_modules=[ext for ext in [animation_utils_extension, artnet_utils_extension, rpi_ws281x_extension] if ext is not None],
    cmdclass={'build_ext': build_ext},
    include_package_data=True,
    entry_points={
        'console_scripts': [
            'ledcontrol=ledcontrol:main'
        ]
    },
    license='MIT',
    classifiers=[
        # Trove classifiers
        # Full list: https://pypi.python.org/pypi?%3Aaction=list_classifiers
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy'
    ]
)
