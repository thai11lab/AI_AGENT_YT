import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.schemas import MasterScript  # noqa: E402
from tools.assemble import assemble_package  # noqa: E402
from core.timing import finalize_timing, budget_report  # noqa: E402


def test_end_to_end_package_assembly_vietnamese(tmp_path):
    """Kiểm tra việc xuất xưởng trọn vẹn 1 production_package tiếng Việt với đủ file theo hợp đồng Phase 2."""
    sample_path = Path(__file__).resolve().parents[1] / "samples" / "master_script.sample.vi.json"
    script = MasterScript.model_validate_json(sample_path.read_text(encoding="utf-8"))
    
    out_dir = assemble_package(
        script=script,
        evidence=[],
        out_root=tmp_path,
        quality={"exit_reason": "PASSED", "fss_score": 0.88},
        models_used={"autopsy": "gemini-3.5-flash", "writer": "gemini-3.5-flash"}
    )
    
    # 1. Đảm bảo toàn bộ 7 file hợp đồng đều xuất hiện
    files = {p.name for p in out_dir.iterdir()}
    required = {
        "master_script.json",
        "asset_manifest.json",
        "style_bible.json",
        "voiceover_full.txt",
        "evidence_dossier.json",
        "quality_report.json",
        "package_manifest.json"
    }
    assert required.issubset(files)
    
    # 2. Đọc lại master_script.json và kiểm tra tính toàn vẹn
    reloaded = MasterScript.model_validate_json((out_dir / "master_script.json").read_text(encoding="utf-8"))
    assert reloaded.language == "vi"
    assert len(reloaded.scenes) == 8
    
    # 3. Kiểm tra voiceover_full.txt đã được nối chuẩn
    vo_full = (out_dir / "voiceover_full.txt").read_text(encoding="utf-8")
    assert "máy in kẹt giấy" in vo_full
    
    # 4. Kiểm tra checksum trong package_manifest
    pkg_manifest = json.loads((out_dir / "package_manifest.json").read_text(encoding="utf-8"))
    assert len(pkg_manifest["checksums"]) == 6

