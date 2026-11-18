"""Zero-dependency Telegram MCP Server (stdio JSON-RPC 2.0) cho Antigravity / AI_AGENT_YT.
Cho phép AI Agent gửi tin nhắn, gửi ảnh/video thành phẩm và đọc lệnh mới từ Telegram.

Biến môi trường:
- TELEGRAM_BOT_TOKEN: Token bot lấy từ @BotFather (bắt buộc)
- TELEGRAM_CHAT_ID: Chat ID mặc định để gửi/nhận tin nhắn (tùy chọn, nên đặt)
- TELEGRAM_ALLOWED_USER_ID: Chỉ nhận tin nhắn từ User ID này khi gọi get_updates (tùy chọn, bảo mật)
"""
import json
import mimetypes
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional


PROTOCOL_VERSION = "2024-11-05"


def _tg_api(method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError("Thiếu biến môi trường TELEGRAM_BOT_TOKEN")
    url = f"https://api.telegram.org/bot{token}/{method}"
    data = json.dumps(params or {}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"Telegram HTTP {e.code}: {err_body}") from e
    if not body.get("ok"):
        raise RuntimeError(f"Telegram API error: {body}")
    return body["result"]


def _tg_upload(method: str, field_name: str, file_path: Path, fields: Dict[str, str]) -> Dict[str, Any]:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError("Thiếu biến môi trường TELEGRAM_BOT_TOKEN")
    if not file_path.exists():
        raise FileNotFoundError(f"Không tìm thấy file: {file_path}")

    boundary = f"----MCPTelegram{uuid.uuid4().hex}"
    chunks: List[bytes] = []
    for k, v in fields.items():
        if not v:
            continue
        chunks.append(
            (
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="{k}"\r\n\r\n'
                f"{v}\r\n"
            ).encode("utf-8")
        )

    mime_type = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
    chunks.append(
        (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="{field_name}"; filename="{file_path.name}"\r\n'
            f"Content-Type: {mime_type}\r\n\r\n"
        ).encode("utf-8")
    )
    chunks.append(file_path.read_bytes())
    chunks.append(f"\r\n--{boundary}--\r\n".encode("utf-8"))
    body_bytes = b"".join(chunks)

    url = f"https://api.telegram.org/bot{token}/{method}"
    req = urllib.request.Request(
        url,
        data=body_bytes,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    if not body.get("ok"):
        raise RuntimeError(f"Telegram API error: {body}")
    return body["result"]


TOOLS: List[Dict[str, Any]] = [
    {
        "name": "get_bot_info",
        "description": "Kiểm tra thông tin Telegram Bot hiện tại (username, id).",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "send_message",
        "description": "Gửi tin nhắn văn bản tới Telegram chat (mặc định dùng TELEGRAM_CHAT_ID).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Nội dung tin nhắn cần gửi"},
                "chat_id": {"type": "string", "description": "Telegram Chat ID (bỏ trống để dùng TELEGRAM_CHAT_ID)"},
                "parse_mode": {"type": "string", "description": "Markdown hoặc HTML (tùy chọn)"},
            },
            "required": ["text"],
            "additionalProperties": False,
        },
    },
    {
        "name": "get_updates",
        "description": "Đọc các tin nhắn/lệnh mới nhất người dùng gửi cho Telegram Bot.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "Số lượng tin nhắn tối đa (mặc định 10)"},
                "offset": {"type": "integer", "description": "update_id bắt đầu (tùy chọn)"},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "send_photo",
        "description": "Gửi file ảnh (thumbnail/preview) từ máy lên Telegram.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "photo_path": {"type": "string", "description": "Đường dẫn tuyệt đối tới file ảnh"},
                "caption": {"type": "string", "description": "Chú thích kèm ảnh"},
                "chat_id": {"type": "string", "description": "Telegram Chat ID (tùy chọn)"},
            },
            "required": ["photo_path"],
            "additionalProperties": False,
        },
    },
    {
        "name": "send_video",
        "description": "Gửi file video .mp4 thành phẩm từ máy lên Telegram.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "video_path": {"type": "string", "description": "Đường dẫn tuyệt đối tới file .mp4"},
                "caption": {"type": "string", "description": "Chú thích kèm video"},
                "chat_id": {"type": "string", "description": "Telegram Chat ID (tùy chọn)"},
            },
            "required": ["video_path"],
            "additionalProperties": False,
        },
    },
]


def _resolve_chat_id(chat_id: str = "") -> str:
    cid = (chat_id or os.getenv("TELEGRAM_CHAT_ID", "")).strip()
    if not cid:
        raise RuntimeError("Thiếu chat_id và chưa đặt biến môi trường TELEGRAM_CHAT_ID")
    return cid


def _call_tool(name: str, args: Dict[str, Any]) -> Any:
    if name == "get_bot_info":
        return _tg_api("getMe")

    if name == "send_message":
        payload: Dict[str, Any] = {
            "chat_id": _resolve_chat_id(args.get("chat_id", "")),
            "text": args["text"],
        }
        if args.get("parse_mode"):
            payload["parse_mode"] = args["parse_mode"]
        return _tg_api("sendMessage", payload)

    if name == "get_updates":
        payload = {"limit": int(args.get("limit", 10))}
        if args.get("offset") is not None:
            payload["offset"] = int(args["offset"])
        updates = _tg_api("getUpdates", payload)
        allowed_uid = os.getenv("TELEGRAM_ALLOWED_USER_ID", "").strip()
        results = []
        for u in updates:
            msg = u.get("message") or u.get("edited_message") or {}
            sender_id = str((msg.get("from") or {}).get("id", ""))
            if allowed_uid and sender_id != allowed_uid:
                continue
            results.append(
                {
                    "update_id": u.get("update_id"),
                    "chat_id": (msg.get("chat") or {}).get("id"),
                    "from_id": sender_id,
                    "from_username": (msg.get("from") or {}).get("username", ""),
                    "text": msg.get("text", ""),
                    "date": msg.get("date"),
                }
            )
        return results

    if name == "send_photo":
        return _tg_upload(
            "sendPhoto",
            "photo",
            Path(args["photo_path"]),
            {"chat_id": _resolve_chat_id(args.get("chat_id", "")), "caption": args.get("caption", "")},
        )

    if name == "send_video":
        return _tg_upload(
            "sendVideo",
            "video",
            Path(args["video_path"]),
            {"chat_id": _resolve_chat_id(args.get("chat_id", "")), "caption": args.get("caption", "")},
        )

    raise ValueError(f"Unknown tool: {name}")


def handle_request(req: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    method = req.get("method")
    req_id = req.get("id")
    params = req.get("params") or {}

    if method == "notifications/initialized":
        return None

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "telegram-mcp-server", "version": "1.0.0"},
            },
        }

    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": req_id, "result": {"tools": TOOLS}}

    if method == "tools/call":
        tool_name = params.get("name", "")
        tool_args = params.get("arguments") or {}
        try:
            res = _call_tool(tool_name, tool_args)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"content": [{"type": "text", "text": json.dumps(res, ensure_ascii=False, indent=2)}]},
            }
        except Exception as exc:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "isError": True,
                    "content": [{"type": "text", "text": f"Error: {exc}"}],
                },
            }

    if req_id is not None:
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32601, "message": f"Method not found: {method}"},
        }
    return None


def main() -> None:
    for raw_line in sys.stdin:
        line = raw_line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            continue
        resp = handle_request(req)
        if resp is not None:
            sys.stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
