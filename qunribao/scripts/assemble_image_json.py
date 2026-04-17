#!/usr/bin/env python3
"""
组装生图 JSON 配置文件

从 qunribao 配置和模板中读取默认值，与 CLI 参数合并，输出 quick-img 可用的 JSON 文件。

用法:
    python assemble_image_json.py \
        --prompt "精炼后的日报内容" \
        --date 2026-04-14 \
        --count 2 \
        --output temp/image_config.json
"""

import argparse
import json
import sys
from pathlib import Path

# 设置 stdout 编码
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


def load_config_defaults() -> dict:
    """从 config_loader 加载默认配置"""
    try:
        from config_loader import ConfigLoader
        loader = ConfigLoader()
        config = loader.load(validate=False)
        return config
    except Exception:
        return {}


def get_style_guide_path() -> str:
    """获取风格指南文件的绝对路径"""
    style_path = Path(__file__).parent.parent / "assets" / "templates" / "日报生图风格.md"
    if style_path.exists():
        return str(style_path.resolve())
    return ""


def main():
    parser = argparse.ArgumentParser(
        description="组装生图 JSON 配置文件",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument("--prompt", "-p", required=True,
                       help="精炼后的日报内容（必填）")
    parser.add_argument("--date", "-d", required=True,
                       help="日报日期，格式 YYYY-MM-DD")
    parser.add_argument("--count", "-n", type=int, default=None,
                       help="生成数量（默认从配置读取）")
    parser.add_argument("--ratio", "-r", default=None,
                       help="宽高比（默认从配置读取）")
    parser.add_argument("--size", "-s", default=None,
                       help="分辨率（默认从配置读取）")
    parser.add_argument("--output", "-o", default=None,
                       help="输出 JSON 文件路径（默认写入 tempDir）")

    args = parser.parse_args()

    # 加载配置默认值
    config = load_config_defaults()

    # 从配置中提取默认值
    last_task = config.get("上次任务", {})
    dirs = config.get("目录", {})
    temp_dir = dirs.get("tempDir", "temp")
    output_dir = dirs.get("outputDir", "reports/daily")

    # 获取风格指南路径
    style_guide = get_style_guide_path()

    # 合并：配置默认值 < CLI 参数覆盖
    image_count = args.count or last_task.get("imageCount", 1)
    image_ratio = args.ratio or last_task.get("imageRatio", "4:5")
    image_size = args.size or last_task.get("imageSize", "2K")

    # 确定输出目录
    output_dir_resolved = Path(output_dir).resolve() / "images"

    # 构造文件名
    date_str = args.date.replace("-", "")
    filename = f"群日报-{args.date}"

    # 组装 JSON
    json_config = {
        "prompt": args.prompt,
        "style_guide": style_guide,
        "count": int(image_count),
        "ratio": image_ratio,
        "size": image_size,
        "output_dir": str(output_dir_resolved),
        "filename": filename,
    }

    # 确定输出路径
    if args.output:
        output_path = Path(args.output)
    else:
        temp_path = Path(temp_dir)
        temp_path.mkdir(parents=True, exist_ok=True)
        output_path = temp_path / f"image_config_{date_str}.json"

    # 写入 JSON
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(json_config, f, ensure_ascii=False, indent=2)

    # 输出文件路径（供 Claude 获取）
    print(str(output_path.resolve()))


if __name__ == "__main__":
    main()
