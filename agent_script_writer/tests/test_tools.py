import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.schemas import EvidenceItem, MasterScript  # noqa: E402
from tools.verify import verify_evidence, classify_tier, dedupe_facts  # noqa: E402
from tools.scoring import compute_fss, passed, fact_keys, new_unique_facts  # noqa: E402
from tools.assemble import assemble_package  # noqa: E402

PAGE = {"https://court.example.gov/case.pdf":
        "# Exhibit 12\n\nAt **11:47 PM** the clerk logged a transfer of $412,000 from account 774-A."}


def ev(i, quote, url="https://court.example.gov/case.pdf", **kw):
    base = dict(evidence_id=f"EV_{i:03d}", hypothesis_id="HYP_01", source_url=url,
                factual_claim=f"claim {i}", verbatim_quote=quote)
    base.update(kw)
    return EvidenceItem(**base)


def test_verify_accepts_real_quote_with_markdown_noise():
    assert verify_evidence(ev(1, "At 11:47 PM the clerk logged a transfer of $412,000"), PAGE)


def test_verify_rejects_fabricated_quote():
    assert not verify_evidence(ev(1, "At 9:00 AM the manager approved a transfer of $999,000"), PAGE)


def test_verify_rejects_unknown_url_and_short_quote():
    assert not verify_evidence(ev(1, "At 11:47 PM the clerk logged", url="https://other.com/x"), PAGE)
    assert not verify_evidence(ev(1, "clerk logged"), PAGE)


def test_classify_tier():
    assert classify_tier("https://www.sec.gov/litigation/x.pdf") == "PRIMARY"
    assert classify_tier("https://arxiv.org/abs/1234") == "ACADEMIC"
    assert classify_tier("https://www.reuters.com/world/x") == "JOURNALISM"
    assert classify_tier("https://someblog.com/post") == "SECONDARY"


def test_dedupe():
    a, b = ev(1, "q" * 25), ev(2, "q" * 25)       # cùng quote
    assert len(dedupe_facts([a, b])) == 1


def full_vault():
    v = []
    for i in range(10):
        e = ev(i, f"unique quote number {i} with enough length",
               url=f"https://court.example.gov/{i}.pdf" if i < 3 else "https://blog.com/x",
               exact_timestamp_or_date=f"2016-03-0{i % 9 + 1} 11:4{i % 9}",
               quantitative_metric=f"${i}00,000", tangible_artifact_desc="beige laser printer")
        e.source_tier = classify_tier(e.source_url)
        e.verified = True
        v.append(e)
    return v


def test_fss_counts_only_verified():
    v = full_vault()
    assert compute_fss(v) > 0.7
    for e in v:
        e.verified = False
    assert compute_fss(v) == 0.0


def test_fss_penalty_and_pass():
    v = full_vault()
    assert passed(v)
    assert compute_fss(v, contradictions=3) < compute_fss(v)


def test_new_unique_facts():
    v = full_vault()
    keys = fact_keys(v[:6])
    assert new_unique_facts(keys, v) == 4


def test_assemble_package(tmp_path):
    sample = Path(__file__).resolve().parents[1] / "samples" / "master_script.sample.en.json"
    script = MasterScript.model_validate_json(sample.read_text(encoding="utf-8"))
    out = assemble_package(script, full_vault(), tmp_path, quality={"exit_reason": "PASSED"})
    names = {p.name for p in out.iterdir()}
    assert names == {"master_script.json", "style_bible.json", "asset_manifest.json",
                     "evidence_dossier.json", "voiceover_full.txt", "quality_report.json",
                     "package_manifest.json"}
    MasterScript.model_validate_json((out / "master_script.json").read_text(encoding="utf-8"))
    manifest = json.loads((out / "package_manifest.json").read_text())
    assert len(manifest["checksums"]) == 6
    am = json.loads((out / "asset_manifest.json").read_text())
    assert am["document_assets"][0]["used_in_scenes"] == ["S005"]

