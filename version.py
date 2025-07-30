"""
Version information for Empyrion Web Helper.

This module provides version constants for the application.
"""

__version__ = "0.5.5"
__version_info__ = (0, 5, 5)

# Version history markers for development tracking
MAJOR = 0  # Incompatible API changes
MINOR = 5  # Backward-compatible functionality additions  
PATCH = 5  # Backward-compatible bug fixes

def get_version():
    """Return the current version string."""
    return __version__

def get_version_info():
    """Return the current version as a tuple."""
    return __version_info__