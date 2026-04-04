#!/usr/bin/env python3
"""图片描述合并与替换脚本

功能：
1. 合并多个 subagent 写入的部分 JSON 文件为一个完整描述映射
2. 读取 chat_context，将 [图片|file:///...] 替换为描述文本
3. 输出 enriched chat_context
4. 清理临时 JSON 文件

用法：
    python scripts/replace_images.py \
        --context temp/chat_context_20260329.md \
        --descriptions-dir temp/image_desc_20260329/ \
        --output temp/chat_context_20260329.md
"""

import json
import re
import argparse
import os
import glob
import sys

# Fix Windows encoding issues
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')


def main():
    parser = argparse.ArgumentParser(description='图片描述合并与替换')
    parser.add_argument('--context', required=True, help='chat_context 文件路径')
    parser.add_argument('--descriptions-dir', required=True, help='subagent 写入的 JSON 文件所在目录')
    parser.add_argument('--output', help='输出文件路径（默认覆盖 context 文件）')
    args = parser.parse_args()

    # 1. 合并所有 batch JSON 文件，并统一 key 为无 file:/// 前缀的本地路径
    descriptions = {}
    json_files = sorted(glob.glob(os.path.join(args.descriptions_dir, '*.json')))

    if not json_files:
        print(f"警告: 未找到 JSON 文件 ({args.descriptions_dir}/*.json)")
        return

    def normalize_path(p):
        """去除 file:/// 前缀，统一路径分隔符"""
        if p.startswith('file:///'):
            p = p[8:]
        elif p.startswith('file://'):
            p = p[7:]
        return os.path.normpath(p)

    for json_file in json_files:
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                batch = json.load(f)
                for k, v in batch.items():
                    descriptions[normalize_path(k)] = v
        except (json.JSONDecodeError, IOError) as e:
            print(f"警告: 跳过无效文件 {json_file}: {e}")

    print(f"合并完成: {len(json_files)} 个文件, {len(descriptions)} 张图片")

    # 2. 读取 chat_context
    with open(args.context, 'r', encoding='utf-8') as f:
        content = f.read()

    # 3. 替换所有 [图片|path] 占位符
    # 匹配 (可能有 "> " 前缀)[图片|path]
    pattern = r'^(>\s*)?\[图片\|([^\]]+)\]'

    matched = 0
    replaced = 0

    def replace_image(match):
        nonlocal matched, replaced
        matched += 1
        prefix = match.group(1) or ''
        path = normalize_path(match.group(2))
        desc = descriptions.get(path)
        if desc:
            replaced += 1
            return f"{prefix}[图片描述: {desc}]"
        else:
            return f"{prefix}[图片]"

    content = re.sub(pattern, replace_image, content, flags=re.MULTILINE)

    # 4. 输出
    output_path = args.output or args.context
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"替换完成: {replaced}/{matched} 张图片已处理")

    # 5. 清理临时 JSON 文件
    for json_file in json_files:
        os.remove(json_file)
    try:
        os.rmdir(args.descriptions_dir)
        print(f"已清理临时目录: {args.descriptions_dir}")
    except OSError:
        print(f"警告: 临时目录非空，未删除: {args.descriptions_dir}")


if __name__ == '__main__':
    main()
