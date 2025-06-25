try:
    import importlib.metadata
    try:
        __version__ = importlib.metadata.metadata("bloom").get("version")
    except importlib.metadata.PackageNotFoundError:
        __version__ = 'unset'
except (ImportError, OSError):
    __version__ = 'unset'
