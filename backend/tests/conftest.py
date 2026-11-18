"""Shared test setup: a fixed master key so tests never touch dev key files."""

import base64
import os

# Must be set before any app module imports app.config.
os.environ.setdefault("ENCRYPTION_MASTER_KEY", base64.b64encode(bytes(range(32))).decode())
