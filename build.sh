#!/usr/bin/env bash
# Render 构建脚本
set -e

pip install -r requirements.txt
python init_db.py
