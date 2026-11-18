"""Kiểm tra trạng thái tài khoản, số dư Credits và hạn mức 1.000 request/ngày trên OpenRouter."""
import json
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.config import get_key  # noqa: E402


def main():
    key = get_key("OPENROUTER_API_KEY")
    headers = {"Authorization": f"Bearer {key}"}

    with httpx.Client(timeout=15.0) as client:
        r_key = client.get("https://openrouter.ai/api/v1/key", headers=headers).json()
        r_cred = client.get("https://openrouter.ai/api/v1/credits", headers=headers).json()

    key_data = r_key.get("data", {})
    cred_data = r_cred.get("data", {})

    total_credits = cred_data.get("total_credits", 0.0)
    total_usage = cred_data.get("total_usage", 0.0)
    balance = round(total_credits - total_usage, 4)
    is_free_tier = key_data.get("is_free_tier", True)

    print("=" * 60)
    print("TRẠNG THÁI TÀI KHOẢN OPENROUTER")
    print("=" * 60)
    print(f"- Tổng đã nạp (Total Credits) : ${total_credits:.2f}")
    print(f"- Đã sử dụng (Total Usage)    : ${total_usage:.4f}")
    print(f"- Số dư hiện tại (Balance)    : ${balance:.4f}")
    print(f"- is_free_tier                : {is_free_tier}")
    if not is_free_tier or total_credits >= 10.0:
        print("=> ĐẶC QUYỀN : ĐÃ MỞ KHÓA 1.000 REQUEST :free / NGÀY (Paid Tier)!")
    else:
        print("=> ĐẶC QUYỀN : Đang ở mức 50 request :free / ngày (chưa đủ $10).")
    print("- Chi tiết JSON từ OpenRouter :")
    print(json.dumps({"key_info": key_data, "credits": cred_data}, indent=2, ensure_ascii=False))
    print("=" * 60)


if __name__ == "__main__":
    main()
