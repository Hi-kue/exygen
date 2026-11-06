from __future__ import annotations

import os

# Tests must never write to the real Langfuse project, even when apps/agent/.env enables
# it. This has to run before 'src' is imported, because the client reads it on import.
os.environ["LANGFUSE_IS_TELEMETRY_ENABLED"] = "false"
