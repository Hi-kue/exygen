"""Clients

The Docling client is not re-exported here: import it from 'src.clients.docling_client'.
It loads Docling, which takes several seconds, so re-exporting it would slow down every
import of the other clients, and with them every import of 'src'.
"""

from src.clients.clef_client import clef_client
from src.clients.langfuse_client import langfuse_client

__version__ = "1.0.0"
__all__ = ["clef_client", "langfuse_client"]
