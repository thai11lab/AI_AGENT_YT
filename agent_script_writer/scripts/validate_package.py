"""Kiểm tra hợp đồng: python scripts/validate_package.py <master_script.json>
Phase 2 nên gọi hàm này đầu tiên trước khi sinh media."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.schemas import MasterScript  # noqa: E402
from core.timing import budget_report  # noqa: E402

path = Path(sys.argv[1])
script = MasterScript.model_validate_json(path.read_text(encoding="utf-8"))
print("OK schema", script.schema_version, script.language, f"{len(script.scenes)} scenes")
print(json.dumps(budget_report(script), indent=2, ensure_ascii=False))

