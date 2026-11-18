#!/bin/bash
# Khởi chạy giao diện Faceless Studio Mission Control UI (v3.1)
cd "$(dirname "$0")/agent_script_writer"
echo "Đang khởi động Mission Control Dashboard tại http://localhost:8501 ..."
.venv/bin/streamlit run app_mission_control.py --server.headless=false --server.port=8501

