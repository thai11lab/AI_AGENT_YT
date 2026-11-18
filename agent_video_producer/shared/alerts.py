"""Discord Error Alerting & Realtime Project Status Tracker."""
import json
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from shared.env import get_env_key


_LEVEL_COLORS = {
    "error": 0xE74C3C,
    "warning": 0xF39C12,
    "success": 0x2ECC71,
    "info": 0x3498DB,
}


def send_discord_alert(
    webhook_url: str = "",
    title: str = "Faceless Studio Alert",
    message: str = "",
    level: str = "error",
    fields: Optional[List[Dict[str, Any]]] = None,
) -> Tuple[bool, str]:
    """Gửi cảnh báo Embed qua Discord Webhook. Không làm sập pipeline nếu mạng lỗi."""
    url = (webhook_url or get_env_key("DISCORD_WEBHOOK_URL")).strip()
    if not url:
        return False, "Chưa cấu hình DISCORD_WEBHOOK_URL"

    embed: Dict[str, Any] = {
        "title": title[:256],
        "description": (message or "(No details)")[:4000],
        "color": _LEVEL_COLORS.get(level, 0xE74C3C),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    if fields:
        embed["fields"] = [
            {
                "name": str(f.get("name", ""))[:256],
                "value": str(f.get("value", ""))[:1024] or "-",
                "inline": bool(f.get("inline", True)),
            }
            for f in fields[:25]
        ]

    payload = json.dumps({"username": "Faceless Studio Bot", "embeds": [embed]}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "FacelessStudio/3.2",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            return (200 <= resp.status < 300), f"HTTP {resp.status}"
    except urllib.error.HTTPError as e:
        return False, f"HTTP {e.code}: {e.reason}"
    except Exception as e:
        return False, str(e)


def write_live_status(
    package_dir: Path,
    status: str,
    current_step: str,
    current_scene: str = "",
    done_scenes: int = 0,
    total_scenes: int = 0,
    error_msg: str = "",
    channel_id: str = "",
) -> Path:
    """Ghi file live_status.json nguyên tử để Dashboard tổng quan đọc realtime."""
    out_dir = Path(package_dir) / "phase2_output"
    out_dir.mkdir(parents=True, exist_ok=True)
    status_path = out_dir / "live_status.json"
    data = {
        "run_id": Path(package_dir).name,
        "status": status,
        "current_step": current_step,
        "current_scene": current_scene,
        "done_scenes": done_scenes,
        "total_scenes": total_scenes,
        "progress_pct": round((done_scenes / total_scenes) * 100, 1) if total_scenes > 0 else 0.0,
        "error_msg": error_msg,
        "channel_id": channel_id,
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    tmp = status_path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(status_path)
    return status_path


def _find_thumbnail(pkg_dir: Path) -> str:
    """Tìm ảnh đại diện đầu tiên trong phase2_output/visual để hiển thị trên Dashboard."""
    visual_dir = pkg_dir / "phase2_output" / "visual"
    if visual_dir.exists():
        for ext in ("*.png", "*.jpg", "*.jpeg", "*.webp"):
            imgs = sorted(visual_dir.glob(ext))
            if imgs:
                return str(imgs[0])
    return ""


def scan_all_projects(packages_root: Path) -> List[Dict[str, Any]]:
    """Quét toàn bộ thư mục production_package để tổng hợp trạng thái realtime cho Dashboard."""
    if not packages_root.exists():
        return []

    projects: List[Dict[str, Any]] = []
    for pkg in sorted(packages_root.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
        if not pkg.is_dir():
            continue
        ms_path = pkg / "master_script.json"
        if not ms_path.exists():
            continue

        try:
            ms = json.loads(ms_path.read_text(encoding="utf-8"))
        except Exception:
            continue

        scenes = ms.get("scenes") or []
        total_scenes = len(scenes)
        lang = ms.get("language", "en")

        out_dir = pkg / "phase2_output"
        live_path = out_dir / "live_status.json"
        manifest_path = out_dir / "phase2_manifest.json"
        qa_path = out_dir / "qa_report.json"

        live = {}
        if live_path.exists():
            try:
                live = json.loads(live_path.read_text(encoding="utf-8"))
            except Exception:
                live = {}

        manifest = {}
        if manifest_path.exists():
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            except Exception:
                manifest = {}

        qa_report = {}
        if qa_path.exists():
            try:
                qa_report = json.loads(qa_path.read_text(encoding="utf-8"))
            except Exception:
                qa_report = {}

        done_motion = len(manifest.get("motion_outputs") or {})
        done_scenes = live.get("done_scenes") if live.get("status") == "RUNNING" else done_motion
        eff_total = live.get("total_scenes") or total_scenes

        final_mp4 = manifest.get("final_video_path") or ""
        if final_mp4 and not Path(final_mp4).exists():
            final_mp4 = ""

        qa_status = qa_report.get("qa_status", "")
        if live.get("status") in {"RUNNING", "ERROR"}:
            status = live["status"]
        elif final_mp4 and qa_status == "PASSED":
            status = "COMPLETED"
        elif final_mp4 and qa_status == "WARNING":
            status = "WARNING"
        elif final_mp4:
            status = "COMPLETED"
        elif done_motion > 0:
            status = "PAUSED"
        else:
            status = "PENDING"

        projects.append(
            {
                "run_id": pkg.name,
                "package_dir": str(pkg),
                "language": lang,
                "channel_id": live.get("channel_id") or manifest.get("channel_id") or "-",
                "total_scenes": eff_total,
                "done_scenes": done_scenes,
                "progress_pct": round((done_scenes / eff_total) * 100, 1) if eff_total > 0 else 0.0,
                "status": status,
                "current_step": live.get("current_step") or ("Hoàn tất" if status == "COMPLETED" else "Chờ dựng Phase 2"),
                "current_scene": live.get("current_scene", ""),
                "error_msg": live.get("error_msg", ""),
                "updated_at": live.get("updated_at") or datetime.fromtimestamp(pkg.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                "thumbnail_path": _find_thumbnail(pkg),
                "final_video_path": final_mp4,
                "qa_status": qa_status,
                "qa_report": qa_report,
            }
        )
    return projects
