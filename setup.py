#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys, io, os, subprocess
from setuptools import find_packages, setup, Extension
from setuptools.command.build_ext import build_ext

def is_raspberrypi():
    try:
        with io.open('/sys/firmware/devicetree/base/model', 'r') as m:
            if 'raspberry pi' in m.read().lower():
                return True
    except Exception:
        pass
    return False

requirements = [
    'Flask==2.2.2',
    'RestrictedPython>=5.2',
    'sacn>=1.8.1',
    'HAP-python==4.4.0',
    'pyopenssl==22.1.0',
    'numpy==1.26.4',
    'pyserial>=3.5',
    'Werkzeug==2.2.2',
] + (['bjoern>=3.2.1'] if sys.platform.startswith('linux') else []) + (
    ['rpi5-ws2812'] if is_raspberrypi() else ['pyfastnoisesimd>=0.4.2']
)

# SWIG extension for animation utilities (performance-critical functions)
animation_utils_extension = None

class SwigBuildExt(build_ext):
    """Custom build_ext to run SWIG if available"""
    def run(self):
        # Check if SWIG is available
        try:
            subprocess.check_call(['swig', '-version'], 
                                 stdout=subprocess.DEVNULL, 
                                 stderr=subprocess.DEVNULL)
            has_swig = True
        except (subprocess.CalledProcessError, FileNotFoundError):
            has_swig = False
            print("Warning: SWIG not found. Animation utilities C extension will not be built.")
            print("Install SWIG with: sudo apt-get install swig (or equivalent)")
            print("The software will work with Python fallback implementations.")
        
        if has_swig:
            # Run SWIG to generate wrapper
            swig_cmd = [
                'swig',
                '-python',
                '-o', 'ledcontrol/driver/ledcontrol_animation_utils_wrap.c',
                'ledcontrol/driver/ledcontrol_animation_utils.i'
            ]
            try:
                subprocess.check_call(swig_cmd)
                print("SWIG generated animation utilities wrapper successfully")
            except subprocess.CalledProcessError as e:
                print(f"Warning: SWIG failed: {e}")
                print("The software will work with Python fallback implementations.")
                return
            
            # Continue with normal build
            super().run()
        else:
            print("Skipping C extension build (SWIG not available)")

# Only build extension if we're on a system with a compiler
# The extension provides better performance but is not required
if sys.platform.startswith('linux'):
    animation_utils_extension = Extension(
        '_ledcontrol_animation_utils',
        sources=['ledcontrol/driver/ledcontrol_animation_utils_wrap.c'],
        include_dirs=['ledcontrol/driver'],
        extra_compile_args=['-O3', '-ffast-math', '-std=c99'],
    )

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
    ext_modules=[animation_utils_extension] if animation_utils_extension else [],
    include_package_data=True,
    entry_points={
        'console_scripts': [
            'ledcontrol=ledcontrol:main'
        ]
    },
    cmdclass={'build_ext': SwigBuildExt} if animation_utils_extension else {},
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
