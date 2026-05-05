"""pubmed-digest: biotech literature summarization CLI with metadata-first retrieval."""

from .config import DEFAULT_MODELS_PATH, RuntimeConfig, load_runtime_config
from .digest.schema import Citation, Digest, PaperCard

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "Citation",
    "DEFAULT_MODELS_PATH",
    "Digest",
    "PaperCard",
    "RuntimeConfig",
    "load_runtime_config",
]
