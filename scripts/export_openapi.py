from __future__ import annotations

import json
from pathlib import Path

from hearsay_api.main import app


def main() -> None:
    repository_root = Path(__file__).resolve().parents[1]
    output = repository_root / "openapi.json"
    output.write_text(json.dumps(app.openapi(), indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {output.relative_to(repository_root)}")


if __name__ == "__main__":
    main()
