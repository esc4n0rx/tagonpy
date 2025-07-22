"""
TagonPy Assets System
Sistema de gerenciamento de assets estáticos com Tailwind CSS e CDN fallback
"""

from .asset_builder import AssetBuilder
from .tailwind_manager import TailwindManager
from .cdn_fallback import TailwindCDNManager

__all__ = [
    'AssetBuilder',
    'TailwindManager', 
    'TailwindCDNManager'
]