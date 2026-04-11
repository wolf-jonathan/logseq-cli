from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("logseq-cli")
except PackageNotFoundError:
    __version__ = "0.2.5"
