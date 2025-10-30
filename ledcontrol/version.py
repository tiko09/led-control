# led-control WS2812B LED Controller Server
# Copyright 2025 jackw01. Released under the MIT License (see LICENSE for details).

import subprocess
import os
from pathlib import Path

def get_git_version():
    """
    Get current Git version information.
    Returns a dictionary with commit hash, branch, and tag.
    """
    try:
        # Get the git directory (works from anywhere in the repo)
        git_dir = Path(__file__).parent.parent / '.git'
        
        if not git_dir.exists():
            return {
                'commit': 'unknown',
                'branch': 'unknown',
                'tag': None,
                'version_string': 'unknown'
            }
        
        # Change to the repository root directory
        repo_dir = Path(__file__).parent.parent
        
        # Get current commit hash (short)
        try:
            commit = subprocess.check_output(
                ['git', 'rev-parse', '--short', 'HEAD'],
                cwd=repo_dir,
                stderr=subprocess.DEVNULL
            ).decode('utf-8').strip()
        except:
            commit = 'unknown'
        
        # Get current branch
        try:
            branch = subprocess.check_output(
                ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
                cwd=repo_dir,
                stderr=subprocess.DEVNULL
            ).decode('utf-8').strip()
        except:
            branch = 'unknown'
        
        # Get current tag (if any)
        try:
            tag = subprocess.check_output(
                ['git', 'describe', '--tags', '--exact-match'],
                cwd=repo_dir,
                stderr=subprocess.DEVNULL
            ).decode('utf-8').strip()
        except:
            tag = None
        
        # Build version string
        if tag:
            version_string = f"{tag} ({branch}@{commit})"
        else:
            version_string = f"{branch}@{commit}"
        
        return {
            'commit': commit,
            'branch': branch,
            'tag': tag,
            'version_string': version_string
        }
        
    except Exception as e:
        return {
            'commit': 'unknown',
            'branch': 'unknown',
            'tag': None,
            'version_string': 'unknown',
            'error': str(e)
        }

# Cache the version at import time
_cached_version = None

def get_version_string():
    """Get cached version string"""
    global _cached_version
    if _cached_version is None:
        _cached_version = get_git_version()
    return _cached_version['version_string']

def get_version_info():
    """Get cached version info dictionary"""
    global _cached_version
    if _cached_version is None:
        _cached_version = get_git_version()
    return _cached_version
