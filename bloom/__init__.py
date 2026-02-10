import sys

try:
    if sys.version_info[0:2] < (3, 10):
        import importlib_metadata
    else:
        import importlib.metadata as importlib_metadata
    try:
        __version__ = importlib_metadata.metadata("bloom").get("version")
    except importlib_metadata.PackageNotFoundError:
        __version__ = 'unset'
except (ImportError, OSError):
    __version__ = 'unset'
