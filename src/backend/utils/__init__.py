"""
Backend Utilities Module

Provides utility functions for backend operations including compression,
data processing, and file handling.
"""

from .compression import (
    compress_file,
    decompress_file,
    compress_string,
    decompress_string,
    compress_data,
    decompress_data,
    create_archive,
    extract_archive,
    get_compression_ratio,
    CompressionFormat,
)

__all__ = [
    "compress_file",
    "decompress_file",
    "compress_string",
    "decompress_string",
    "compress_data",
    "decompress_data",
    "create_archive",
    "extract_archive",
    "get_compression_ratio",
    "CompressionFormat",
]
