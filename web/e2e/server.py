# the gateway for the browser tests: same app, but the audit log and rule edits go to a scratch folder, not data/
#   uv run --frozen python web/e2e/server.py 8101
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import uvicorn

from chaperone import gateway, policy
from chaperone.app import app

scratch = Path(tempfile.mkdtemp(prefix="chaperone-e2e-"))
gateway.AUDIT_PATH = scratch / "audit.jsonl"
policy.LOCAL_PATH = scratch / "policies.local.yaml"
uvicorn.run(app, host="127.0.0.1", port=int(sys.argv[1]), log_level="warning")
