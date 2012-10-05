try:
    import pkg_resources
    __version__ = pkg_resources.require("bloom")[0].version
except ImportError:
    __version__ = 'unset'
