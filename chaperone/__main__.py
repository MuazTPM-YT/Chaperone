import os
import sys

import uvicorn

from . import policy
from .detect import detect
from .gateway import need

# fail loud on missing config before the server starts, not mid-demo
for name in ("INTERNAL_LLM_BASE_URL", "INTERNAL_LLM_MODEL", "EXTERNAL_LLM_BASE_URL", "EXTERNAL_LLM_MODEL",
             "AUDIT_HMAC_KEY"):
    need(name)
# a broken rule file must stop the start, not fail the first message
try:
    policy.current()
except policy.PolicyError as exc:
    sys.exit(f"rule error: {exc}")

# load GLiNER and the context model now, so the first demo request is fast
print("warming up models...", flush=True)
print("context layer ok" if detect("Warm-up for Priya.").context_ok else "context layer OFFLINE", flush=True)
uvicorn.run("chaperone.app:app", host="127.0.0.1", port=int(os.environ.get("PORT", "8000")))
