#!/usr/bin/env python3
"""
Quick Img - 快速图片生成工具

使用方式:
    # Direct Prompt 模式（默认）
    python generate_image.py --prompt "AI概念图" --ratio 16:9 --size 2K

    # Template 模式 - 模板 + 源文件内容
    python generate_image.py --input report.md --ratio 4:5 --size 2K

    # 批量生成（抽卡）
    python generate_image.py --prompt "landscape" --count 3
"""

import os
import sys
import json
import re
import base64
import argparse
import requests
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List

# 设置 stdout 编码为 UTF-8（解决 Windows 控制台编码问题）
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


def load_config() -> dict:
    """加载配置文件"""
    skill_dir = Path(__file__).parent.parent
    config_path = skill_dir / "assets" / "config.json"

    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_template(template_name: str) -> str:
    """从外部文件加载模板"""
    skill_dir = Path(__file__).parent.parent
    template_path = skill_dir / "assets" / "templates" / f"{template_name}.txt"

    # 如果指定模板不存在，使用默认模板
    if not template_path.exists():
        template_path = skill_dir / "assets" / "templates" / "default.txt"

    with open(template_path, "r", encoding="utf-8") as f:
        return f.read()


def load_style_guide(style_guide_path: str) -> str:
    """从外部文件加载风格指南"""
    path = Path(style_guide_path)
    if not path.exists():
        raise FileNotFoundError(f"风格指南文件不存在: {style_guide_path}")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def parse_json_config(json_path: str) -> dict:
    """从 JSON 文件加载生图配置"""
    path = Path(json_path)
    if not path.exists():
        raise FileNotFoundError(f"JSON 配置文件不存在: {json_path}")
    with open(path, "r", encoding="utf-8") as f:
        config = json.load(f)

    # 验证：prompt 必填
    if not config.get("prompt"):
        raise ValueError("JSON 配置必须包含非空的 'prompt' 字段")

    return config


def load_env() -> str:
    """从 .env 文件加载 API Key"""
    skill_dir = Path(__file__).parent.parent
    env_path = skill_dir / "assets" / ".env"

    if not env_path.exists():
        # 尝试从当前工作目录的 .env 读取
        env_path = Path(".env")

    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("DMX_API_KEY="):
                    return line.split("=", 1)[1].strip()

    # 尝试从环境变量读取
    api_key = os.environ.get("DMX_API_KEY")
    if api_key:
        return api_key

    raise ValueError(
        "未找到 DMX_API_KEY。请完成以下设置:\n"
        "1. 复制 assets/.env.example 为 assets/.env\n"
        "   cp assets/.env.example assets/.env\n"
        "2. 编辑 assets/.env，填入你的 DMX API Key\n"
        "   DMX_API_KEY=sk-your-api-key-here\n"
        "3. 获取 API Key: https://www.dmxapi.cn\n"
        "提示: 也可设置环境变量 DMX_API_KEY"
    )


def render_template_simple(template: str, content: str) -> str:
    """
    极简模式：只替换 {{content}} 变量
    """
    return template.replace("{{content}}", content)


def render_template_advanced(template_name: str, variables: Dict[str, str]) -> str:
    """
    高级模式：渲染模板，支持 {{var}}、{{var|default}} 和条件块 {{#var}}...{{/var}}
    """
    template = load_template(template_name)

    # 处理条件块 {{#var}}...{{/var}}
    def replace_conditional(match):
        var_name = match.group(1)
        content = match.group(2)
        if var_name in variables and variables[var_name]:
            return content
        return ""

    template = re.sub(r'\{\{#(\w+)\}\}(.*?)\{\{/\1\}\}', replace_conditional, template, flags=re.DOTALL)

    # 处理变量 {{var}} 或 {{var|default}}
    def replace_variable(match):
        var_parts = match.group(1).split("|")
        var_name = var_parts[0].strip()
        default_value = var_parts[1].strip() if len(var_parts) > 1 else ""
        return variables.get(var_name, default_value)

    result = re.sub(r'\{\{(\w+(?:\|[^}]+)?)\}\}', replace_variable, template)
    return result


def generate_filename_by_content(content: str, timestamp: str) -> str:
    """
    基于内容生成文件名（简化版，实际使用时由 AI 总结）
    返回格式: 简短描述_时间戳.png
    """
    # 检查是否是日报
    if "日报" in content or "daily" in content.lower():
        # 尝试提取日期
        date_match = re.search(r'(\d{4}[-/年]\d{1,2}[-/月]\d{1,2})', content)
        if date_match:
            date_str = date_match.group(1).replace("-", "").replace("/", "").replace("年", "").replace("月", "")
            return f"日报_{date_str}_{timestamp}.png"
        return f"日报_{timestamp}.png"

    # 检查是否是海报
    if "海报" in content:
        return f"海报_{timestamp}.png"

    # 检查主题关键词
    keywords = ["AI", "人工智能", "科技", "未来", "设计", "艺术", "自然", "风景"]
    for kw in keywords:
        if kw in content:
            return f"{kw}主题_{timestamp}.png"

    return f"生成图片_{timestamp}.png"


def call_dmx_api(
    api_key: str,
    prompt: str,
    aspect_ratio: str = "1:1",
    image_size: str = "1K",
    image_search: bool = False,
    google_search: bool = False,
    config: dict = None
) -> bytes:
    """调用 DMX API 生成图片"""

    base_url = config["api"]["base_url"]
    endpoint = config["api"]["endpoint"]

    headers = {
        "x-goog-api-key": api_key,
        "Content-Type": "application/json"
    }

    # 构建请求体
    data = {
        "contents": [{
            "parts": [{
                "text": prompt
            }]
        }],
        "generationConfig": {
            "responseModalities": ["IMAGE"],
            "imageConfig": {
                "aspectRatio": aspect_ratio,
            }
        }
    }

    # 添加 image_size 配置（如果支持）
    if image_size != "1K":
        data["generationConfig"]["imageConfig"]["imageSize"] = image_size

    # 添加 tools 配置（搜索功能）
    tools = []
    if google_search or image_search:
        search_types = {}
        if google_search:
            search_types["web_search"] = {}
        if image_search:
            search_types["image_search"] = {}
        tools.append({"google_search": {"search_types": search_types}})

    if tools:
        data["tools"] = tools

    try:
        response = requests.post(
            f"{base_url}{endpoint}",
            headers=headers,
            json=data,
            timeout=300
        )

        if response.status_code != 200:
            raise RuntimeError(f"API 请求失败: {response.status_code}\n{response.text}")

        result = response.json()

        # 解析响应，提取图片数据
        try:
            parts = result["candidates"][0]["content"]["parts"]
            for part in parts:
                if "inlineData" in part:
                    image_data = part["inlineData"]["data"]
                    return base64.b64decode(image_data)
        except (KeyError, IndexError) as e:
            raise RuntimeError(f"解析响应失败: {e}\n响应内容: {result}")

        raise RuntimeError("响应中未找到图片数据")

    except requests.exceptions.Timeout:
        raise RuntimeError("API 请求超时，请稍后重试")
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"网络请求错误: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Quick Img - 快速图片生成，支持 Direct Prompt 和 Template 两种模式",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # Direct Prompt 模式（默认）
  python generate_image.py --prompt "AI概念图" --ratio 16:9 --size 2K

  # Template 模式 - 模板 + 源文件内容
  python generate_image.py --input report.md --ratio 4:5 --size 2K

  # 批量生成（抽卡）
  python generate_image.py --prompt "landscape" --count 3

  # 批量生成 + 保存提示词
  python generate_image.py --prompt "landscape" --count 3 --save-prompts

  # 启用图片搜索
  python generate_image.py --prompt "cat" --image-search

  # JSON 配置文件模式
  python generate_image.py --json config.json

环境变量:
  DMX_API_KEY           DMX API Key（用于图片生成）
        """
    )

    # 模式选择
    parser.add_argument("--input", "-i", help="源文件路径（Template 模式）")
    parser.add_argument("--prompt", "-p", help="直接输入提示词（Direct Prompt 模式）")
    parser.add_argument("--refined-content", "-c", help="直接传入提炼后的内容（已弃用，保留向后兼容）")

    # 高级模式开关
    parser.add_argument("--advanced", "-a", action="store_true",
                       help="启用高级变量注入（已弃用，保留向后兼容）")

    # 模板选择
    parser.add_argument("--template", "-t", default="生图模板",
                       help="模板名称（默认: 生图模板，可选: 海报模板 等）")

    # 模板变量
    parser.add_argument("--var", action="append", dest="variables",
                       help="模板变量 KEY=VALUE（已弃用，保留向后兼容）")

    # 图片参数
    parser.add_argument("--ratio", default=None,
                       help="宽高比 (默认: 4:5，可选: 1:1, 16:9, 9:16, 4:3 等)")
    parser.add_argument("--size", default=None,
                       help="分辨率 (默认: 1K，可选: 0.5K, 1K, 2K, 4K)")
    parser.add_argument("--image-search", action="store_true",
                       help="启用 Image Search 图片搜索功能（让模型参考真实图片生成）")
    parser.add_argument("--google-search", action="store_true",
                       help="启用 Google 搜索工具（使用实时信息生成图像）")

    # 批量生成
    parser.add_argument("--count", "-n", type=int, default=1,
                       help="批量生成数量 (默认: 1)")
    parser.add_argument("--save-prompts", action="store_true",
                       help="保存最终提示词为 .txt 文件")

    # 输出控制
    parser.add_argument("--output-dir", "-o", help="输出目录（手动模式）")
    parser.add_argument("--filename", "-f", help="自定义文件名（覆盖自动总结）")
    parser.add_argument("--style-guide", "-s", help="外部风格指南文件路径（追加到提示词末尾）")
    parser.add_argument("--json", "-j", dest="json_config",
                       help="JSON 配置文件路径（.json），覆盖其他参数")
    parser.add_argument("--dry-run", action="store_true",
                       help="仅打印生成的提示词，不调用 API")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="显示详细日志")

    args = parser.parse_args()

    # --json 覆盖：从 JSON 文件读取配置，覆盖 CLI 参数
    if args.json_config:
        try:
            json_params = parse_json_config(args.json_config)
        except (FileNotFoundError, ValueError, json.JSONDecodeError) as e:
            print(f"错误: {e}")
            sys.exit(1)

        # JSON 字段映射到 argparse 属性
        json_field_map = {
            "prompt": "prompt",
            "style_guide": "style_guide",
            "count": "count",
            "ratio": "ratio",
            "size": "size",
            "output_dir": "output_dir",
            "filename": "filename",
            "image_search": "image_search",
            "google_search": "google_search",
        }
        for json_key, attr_name in json_field_map.items():
            if json_key in json_params and json_params[json_key] is not None:
                setattr(args, attr_name, json_params[json_key])

        # style_guide 为空字符串 → 不追加风格
        if args.style_guide == "":
            args.style_guide = None

    # 验证参数
    if not args.input and not args.prompt:
        parser.error("请提供 --input、--prompt 或 --json 之一")

    if args.prompt and (args.input or args.refined_content):
        parser.error("--prompt 不能与 --input 或 --refined-content 同时使用")

    if args.refined_content and not args.input:
        parser.error("使用 --refined-content 时必须提供 --input 用于确定输出目录")

    # 加载配置
    config = load_config()

    # 确定生成参数（优先命令行参数，其次配置默认值）
    image_params = config.get("image_params", {})
    aspect_ratio = args.ratio or image_params.get("default_ratio", "4:5")
    image_size = args.size or image_params.get("default_size", "1K")
    image_search = args.image_search or image_params.get("default_image_search", False)
    google_search = args.google_search
    template_name = args.template
    batch_count = max(1, args.count)  # 批量生成数量

    # 解析模板变量（仅高级模式）
    variables = {}
    if args.advanced and args.variables:
        for var in args.variables:
            if "=" in var:
                key, value = var.split("=", 1)
                variables[key] = value

    # 模式分支：生成最终提示词
    if args.refined_content:
        # 极简模式 + Claude提炼：直接使用传入的提炼内容
        if not args.input:
            parser.error("使用 --refined-content 时必须提供 --input 用于确定输出目录")

        input_path = Path(args.input)
        template = load_template(template_name)
        final_prompt = render_template_simple(template, args.refined_content)
        mode_label = "极简模式(Claude提炼)"
        output_dir = input_path.parent

    elif args.input:
        # 极简/高级模式
        input_path = Path(args.input)
        if not input_path.exists():
            print(f"错误: 找不到输入文件 {args.input}")
            sys.exit(1)

        # 读取源文件内容
        with open(input_path, "r", encoding="utf-8") as f:
            source_content = f.read()

        # 根据模式选择渲染方式
        if args.advanced:
            # 高级模式：完整模板渲染
            if "content" not in variables:
                variables["content"] = source_content[:2000]  # 限制长度避免超限
            final_prompt = render_template_advanced(template_name, variables)
            mode_label = "高级模式"
        else:
            # 极简模式：直接拼接（模板前缀 + 源文件内容）
            template = load_template(template_name)
            final_prompt = render_template_simple(template, source_content)
            mode_label = "极简模式"

        # 确定输出目录（源文件同目录）
        output_dir = input_path.parent

    else:
        # 手动模式
        final_prompt = args.prompt
        mode_label = "手动模式"

        # 确定输出目录
        if args.output_dir:
            output_dir = Path(args.output_dir)
        else:
            output_dir = Path("output")

    # 确保输出目录存在
    output_dir.mkdir(parents=True, exist_ok=True)

    # 追加外部风格指南
    if args.style_guide:
        try:
            style_content = load_style_guide(args.style_guide)
            final_prompt = final_prompt + "\n\n" + style_content
            mode_label += "+风格指南"
        except FileNotFoundError as e:
            print(f"警告: {e}，将忽略风格指南")

    # 生成基础文件名（不含序号和扩展名）
    timestamp = datetime.now().strftime(config["output"]["timestamp_format"])

    if args.filename:
        base_filename = args.filename
        if base_filename.endswith(".png"):
            base_filename = base_filename[:-4]
    else:
        # 基于内容生成文件名（去掉扩展名）
        base_filename = generate_filename_by_content(final_prompt, timestamp)
        if base_filename.endswith(".png"):
            base_filename = base_filename[:-4]

    # 打印信息
    if args.verbose or args.dry_run:
        print("=" * 50)
        print(f"图片生成配置 - {mode_label}")
        print("=" * 50)
        if args.input:
            print(f"输入文件: {args.input}")
            print(f"模板: {template_name}")
        print(f"宽高比: {aspect_ratio}")
        print(f"分辨率: {image_size}")
        print(f"Image Search: {'启用' if image_search else '关闭'}")
        print(f"Google Search: {'启用' if google_search else '关闭'}")
        print(f"批量生成: {batch_count} 张")
        print(f"保存提示词: {'是' if args.save_prompts else '否'}")
        print(f"输出目录: {output_dir}")
        print("-" * 50)
        print("生成提示词:")
        print(final_prompt)
        print("=" * 50)

    if args.dry_run:
        print("\n[干运行模式] 不调用 API")
        sys.exit(0)

    # 加载 API Key
    try:
        api_key = load_env()
    except ValueError as e:
        print(f"错误: {e}")
        sys.exit(1)

    # 批量生成循环
    print(f"正在生成图片... [{mode_label}]")
    print(f"配置: 宽高比={aspect_ratio}, 分辨率={image_size}, ImageSearch={'开' if image_search else '关'}, GoogleSearch={'开' if google_search else '关'}")
    print(f"批量生成 {batch_count} 张图片...")
    print("-" * 50)

    success_count = 0
    for i in range(1, batch_count + 1):
        # 生成带序号的文件名
        if batch_count > 1:
            filename = f"{base_filename}_{i:02d}.png"
            prompt_filename = f"{base_filename}_{i:02d}.txt"
        else:
            filename = f"{base_filename}.png"
            prompt_filename = f"{base_filename}.txt"

        output_path = output_dir / filename

        print(f"\n[{i}/{batch_count}] 生成中...")

        try:
            image_bytes = call_dmx_api(
                api_key=api_key,
                prompt=final_prompt,
                aspect_ratio=aspect_ratio,
                image_size=image_size,
                image_search=image_search,
                google_search=google_search,
                config=config
            )

            # 保存图片
            with open(output_path, "wb") as f:
                f.write(image_bytes)

            print(f"  ✓ 图片已保存: {filename} ({len(image_bytes) / 1024:.1f} KB)")
            success_count += 1

            # 保存提示词（如果启用）
            if args.save_prompts:
                prompt_path = output_dir / prompt_filename
                with open(prompt_path, "w", encoding="utf-8") as f:
                    f.write(final_prompt)
                print(f"  ✓ 提示词已保存: {prompt_filename}")

        except RuntimeError as e:
            print(f"  ✗ 错误: {e}")
            continue
        except Exception as e:
            print(f"  ✗ 未知错误: {e}")
            continue

    print("-" * 50)
    print(f"完成: {success_count}/{batch_count} 张图片生成成功")
    if success_count > 0:
        print(f"输出目录: {output_dir}")


if __name__ == "__main__":
    main()
