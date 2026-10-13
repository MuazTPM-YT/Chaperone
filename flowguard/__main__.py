import os

import uvicorn

from .detect import detect
from .gateway import need

# fail loud on missing config before the server starts, not mid-demo
for name in ("INTERNAL_LLM_BASE_URL", "INTERNAL_LLM_MODEL", "EXTERNAL_LLM_BASE_URL", "EXTERNAL_LLM_MODEL",
             "AUDIT_HMAC_KEY"):
    need(name)

# load GLiNER and the context model now, so the first demo request is fast
print("warming up models...", flush=True)
print("context layer ok" if detect("Warm-up for Priya.").context_ok else "context layer OFFLINE", flush=True)
uvicorn.run("flowguard.app:app", host="127.0.0.1", port=int(os.environ.get("PORT", "8000")))
