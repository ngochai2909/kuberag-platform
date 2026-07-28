"""Source adapters that normalize external feeds into SourceDocument."""

from ingestion.adapters.nvd import NvdAdapter
from ingestion.adapters.vnexpress import VnExpressAdapter

__all__ = ["NvdAdapter", "VnExpressAdapter"]
