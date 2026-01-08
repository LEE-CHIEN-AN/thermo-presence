#!/bin/bash
# Linux/Mac 安裝腳本：安裝 Supabase 整合所需的套件
# 使用 --no-warn-script-location 來抑制 PATH 警告

echo "正在安裝 Supabase 整合所需的套件..."
echo

python3 -m pip install --no-warn-script-location -r requirements.txt

if [ $? -eq 0 ]; then
    echo
    echo "========================================"
    echo "安裝成功！"
    echo "========================================"
    echo
    echo "下一步："
    echo "1. 設定 Supabase URL 和 API key"
    echo "2. 執行: python main.py --supabase-url <url> --supabase-key <key> --session-id <session>"
else
    echo
    echo "========================================"
    echo "安裝失敗，請檢查錯誤訊息"
    echo "========================================"
fi

