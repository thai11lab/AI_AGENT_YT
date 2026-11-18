"""N8 Assembler: ghi production_package/<run_id>/ theo hợp đồng Phase 2."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from core.schemas import MasterScript, EvidenceItem, SCHEMA_VERSION
from core.timing import finalize_timing, budget_report
from core.render_plan import resolve_render_plan, summarize


def _sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _write_json(p: Path, obj) -> None:
    p.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def build_asset_manifest(script: MasterScript) -> Dict:
    docs, used = {}, {}
    for s in script.scenes:
        if s.document_asset:
            key = (s.document_asset.source_url, s.document_asset.page)
            used.setdefault(key, []).append(s.scene_id)
            docs.setdefault(key, s.document_asset)
    document_assets = [
        {"asset_id": f"DOC_{i + 1:03d}", "source_url": k[0], "page": k[1],
         "highlight_text": docs[k].highlight_text, "used_in_scenes": used[k]}
        for i, k in enumerate(docs)
    ]
    entities = [
        {"entity_token": e.entity_token, "prompt": e.reference_image_prompt, "priority": 1}
        for e in script.plan.style_bible.entity_locks
    ]
    modes: Dict[str, int] = {}
    for s in script.scenes:
        modes[s.visual_mode] = modes.get(s.visual_mode, 0) + 1
    return {
        "entity_reference_images": entities,
        "document_assets": document_assets,
        "counts": {"total_scenes": len(script.scenes), **modes},
        "motion_tier": script.output_spec.motion_tier,
        "render_plan_summary": summarize(resolve_render_plan(script)),
        "estimated_total_duration_sec": script.estimated_total_duration_sec,
    }


def assemble_package(script: MasterScript, evidence: List[EvidenceItem], out_root: Path,
                     quality: Optional[Dict] = None, models_used: Optional[Dict] = None) -> Path:
    """Tính thời gian, kiểm tra hợp đồng lần cuối, ghi toàn bộ gói. Trả về thư mục gói."""
    finalize_timing(script)
    script = MasterScript.model_validate(script.model_dump())      # validate lần cuối
    out = Path(out_root) / script.run_id
    out.mkdir(parents=True, exist_ok=True)

    _write_json(out / "master_script.json", script.model_dump())
    _write_json(out / "style_bible.json", script.plan.style_bible.model_dump())
    _write_json(out / "asset_manifest.json", build_asset_manifest(script))
    _write_json(out / "evidence_dossier.json", [e.model_dump() for e in evidence])

    acts: Dict[int, List[str]] = {}
    for s in script.scenes:
        acts.setdefault(s.act_number, []).append(s.voiceover_text)
    (out / "voiceover_full.txt").write_text(
        "\n\n".join(" ".join(v) for _, v in sorted(acts.items())), encoding="utf-8")

    report = {"budget": budget_report(script), **(quality or {})}
    _write_json(out / "quality_report.json", report)

    files = ["master_script.json", "style_bible.json", "asset_manifest.json",
             "evidence_dossier.json", "voiceover_full.txt", "quality_report.json"]
    _write_json(out / "package_manifest.json", {
        "schema_version": SCHEMA_VERSION,
        "run_id": script.run_id,
        "language": script.language,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "models_used": models_used or {},
        "checksums": {f: _sha256(out / f) for f in files},
    })
    return out

