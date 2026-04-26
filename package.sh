#!/bin/bash

# 打包插件为 zip 文件
# 忽略 .git 目录和 __pycache__ 目录
# 包含当前目录本身

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_NAME="$(basename "$SCRIPT_DIR")"
OUTPUT_FILE="${PLUGIN_NAME}.zip"

echo "开始打包插件: $PLUGIN_NAME"

# 切换到脚本所在目录
cd "$SCRIPT_DIR"

# 删除旧的打包文件
if [ -f "$OUTPUT_FILE" ]; then
    echo "删除旧的打包文件: $OUTPUT_FILE"
    rm "$OUTPUT_FILE"
fi

# 切换到上级目录，打包当前目录
cd ..

# 使用 zip 打包，排除 .git 和 __pycache__
zip -r "$PLUGIN_NAME/$OUTPUT_FILE" "$PLUGIN_NAME" \
    -x "$PLUGIN_NAME/.git/*" \
    -x "$PLUGIN_NAME/.git" \
    -x "$PLUGIN_NAME/__pycache__/*" \
    -x "$PLUGIN_NAME/*/__pycache__/*" \
    -x "$PLUGIN_NAME/*/*/__pycache__/*" \
    -x "$PLUGIN_NAME/*.pyc" \
    -x "$PLUGIN_NAME/main.py.backup" \
    -x "$PLUGIN_NAME/*.zip"

# 移动到插件目录
mv "$PLUGIN_NAME/$OUTPUT_FILE" "$PLUGIN_NAME/" 2>/dev/null || true

echo "打包完成: $SCRIPT_DIR/$OUTPUT_FILE"
echo "文件大小: $(du -h "$SCRIPT_DIR/$OUTPUT_FILE" | cut -f1)"
