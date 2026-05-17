from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = REPO_ROOT.parent


for path in reversed(
    [
        REPO_ROOT,
        REPO_ROOT / "integrations" / "contract-compiler" / "src",
        REPO_ROOT / "integrations" / "guard",
        REPO_ROOT / "integrations" / "proposal-normalizer",
        REPO_ROOT / "integrations" / "cricore" / "src",
        WORKSPACE_ROOT / "waveframe-dev" / "integrations" / "contract-compiler" / "src",
        WORKSPACE_ROOT / "waveframe-dev" / "integrations" / "guard",
        WORKSPACE_ROOT / "waveframe-dev" / "integrations" / "proposal-normalizer",
        WORKSPACE_ROOT / "waveframe-dev" / "integrations" / "cricore" / "src",
        WORKSPACE_ROOT / "cricore-contract-compiler" / "src",
        WORKSPACE_ROOT / "Waveframe-Guard",
        WORKSPACE_ROOT / "proposal-normalizer",
        WORKSPACE_ROOT / "CRI-CORE" / "src",
    ]
):
    if path.exists():
        path_text = str(path)
        if path_text not in sys.path:
            sys.path.insert(0, path_text)
