#!/usr/bin/env python3
"""并行图片分析脚本

功能：
1. 读取 _images.txt 文件中的图片路径列表
2. 并行调用 Vision API 分析每张图片（使用 asyncio + AsyncOpenAI）
3. 自动重试失败的请求（最多 3 次，指数退避）
4. 输出 descriptions.json 文件

用法：
    python scripts/describe_images.py \
        --images-file temp/chat_context_20260403_images.txt \
        --output-dir temp/image_desc_20260403
"""

import asyncio
import base64
import json
import argparse
import os
import sys
from pathlib import Path

from openai import AsyncOpenAI

# Fix Windows encoding issues
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# ── 默认配置（DMX API / qwen3.5-flash）──
DEFAULT_BASE_URL = "https://www.dmxapi.cn/v1"
DEFAULT_MODEL = "qwen3.5-flash"
DEFAULT_API_KEY_ENV = "DMX_API_KEY"
MIN_CONCURRENCY = 5
DEFAULT_CONCURRENCY = 10
DEFAULT_MAX_RETRIES = 3

# ── 备选配置（智谱 GLM）──
FALLBACK_BASE_URL = "https://open.bigmodel.cn/api/paas/v4"
FALLBACK_MODEL = "glm-4.6v-flash"
FALLBACK_API_KEY_ENV = "ANTHROPIC_AUTH_TOKEN"

# ── 描述策略 prompt（7 分类策略）──
UNIFIED_PROMPT = """分析这张图片，按以下策略描述：
1. 纯文本截图：逐字还原所有可见文字
2. 操作界面截图：描述布局，还原界面文字
3. 知识卡片/信息图：还原所有文字，说明逻辑结构
4. 海报/公告：还原标题、时间、地点等所有文字
5. 环境照片：简述场景，提取可见文字
6. 表情包/梗图：简述内容和含义，还原文字
7. 纯表情/贴图（无文字或极少文字的夸张表情图片）：只需用一句话描述传达的情绪或氛围，如"得意""无语""鼓励""惊讶"等，不要描述画面细节
8. 其他：说明图片性质，还原关键内容
请先判断类型，再按对应策略输出。
重要：输出不要使用任何markdown格式（不要用#、**、-等标记），直接使用纯文本，用逗号或句号作为分隔。"""


def encode_image(image_path: str) -> tuple[str, str]:
    """读取图片文件，返回 (base64_data, mime_type)

    Args:
        image_path: 图片路径（可能包含 file:/// 前缀）

    Returns:
        (base64编码的数据, MIME类型)
    """
    # 去除 file:/// 前缀
    path = image_path.replace("file:///", "").replace("file://", "")
    ext = Path(path).suffix.lower()

    # 文件扩展名到 MIME 类型的映射
    mime_map = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".webp": "image/webp",
    }
    mime = mime_map.get(ext, "image/png")

    try:
        with open(path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        return b64, mime
    except FileNotFoundError:
        raise FileNotFoundError(f"图片文件不存在: {path}")
    except Exception as e:
        raise RuntimeError(f"读取图片失败 ({path}): {e}")


async def analyze_one(
    client: AsyncOpenAI,
    semaphore: asyncio.Semaphore,
    image_path: str,
    model: str,
    max_retries: int,
) -> tuple[str, str]:
    """分析单张图片，返回 (image_path, description)

    Args:
        client: AsyncOpenAI 客户端
        semaphore: 并发控制信号量
        image_path: 图片路径
        model: Vision 模型名称
        max_retries: 最大重试次数

    Returns:
        (图片路径, 描述文本或错误信息)
    """
    async with semaphore:
        # 1. 编码图片
        try:
            b64, mime = encode_image(image_path)
        except FileNotFoundError:
            return image_path, "[图片文件不存在]"
        except Exception as e:
            return image_path, f"[图片读取失败: {e}]"

        # 2. 调用 API（带重试）
        for attempt in range(max_retries):
            try:
                resp = await client.chat.completions.create(
                    model=model,
                    messages=[{
                        "role": "user",
                        "content": [
                            {"type": "text", "text": UNIFIED_PROMPT},
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:{mime};base64,{b64}"}
                            },
                        ],
                    }],
                    max_tokens=1024,
                )
                desc = resp.choices[0].message.content
                if desc and desc.strip():
                    return image_path, desc.strip()

                # 空响应，重试
                if attempt < max_retries - 1:
                    await asyncio.sleep(3 * (2 ** attempt))
                    continue
                return image_path, "[图片分析返回空响应]"

            except Exception as e:
                if attempt < max_retries - 1:
                    # 指数退避重试（429 速率限制需要更长等待）
                    wait = 5 * (2 ** attempt)
                    print(f"    重试 {attempt+1}/{max_retries} ({wait}s): {str(e)[:60]}")
                    await asyncio.sleep(wait)
                    continue
                # 最后一次尝试失败
                return image_path, f"[图片分析失败: {str(e)[:100]}]"

        return image_path, "[图片分析超时]"


def load_api_key(env_name: str) -> str:
    """从环境变量或 .env 文件加载 API Key

    查找顺序：
    1. os.environ[env_name]
    2. 技能目录 assets/.env 文件中的 {env_name}=xxx
    """
    # 1. 环境变量
    key = os.environ.get(env_name, "")
    if key:
        return key

    # 2. .env 文件（技能目录/assets/.env）
    skill_dir = Path(__file__).parent.parent
    env_path = skill_dir / "assets" / ".env"
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith(f"{env_name}="):
                    return line.split("=", 1)[1].strip()

    return ""


async def main_async(args):
    # 1. 读取图片列表
    try:
        with open(args.images_file, 'r', encoding='utf-8') as f:
            paths = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"错误: 图片列表文件不存在: {args.images_file}")
        return 1

    if not paths:
        print("无图片需要分析")
        return 0

    # 2. 确保并发数不小于最小值
    concurrency = max(MIN_CONCURRENCY, args.concurrency)
    semaphore = asyncio.Semaphore(concurrency)

    # 3. 创建异步 OpenAI 客户端
    api_key = load_api_key(args.api_key_env)
    if not api_key:
        print(f"错误: 环境变量 {args.api_key_env} 未设置")
        return 1

    client = AsyncOpenAI(api_key=api_key, base_url=args.base_url)

    # 4. 并行分析所有图片
    print(f"开始分析 {len(paths)} 张图片 (并发: {concurrency}, 模型: {args.model})")

    tasks = [
        analyze_one(client, semaphore, path, args.model, args.max_retries)
        for path in paths
    ]
    results = await asyncio.gather(*tasks)

    # 5. 合并结果
    descriptions = dict(results)

    # 6. 写入 JSON
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    output_file = out / "descriptions.json"

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(descriptions, f, ensure_ascii=False, indent=2)

    # 7. 统计
    success = sum(1 for v in descriptions.values() if not v.startswith("["))
    failed = len(descriptions) - success

    print(f"完成: {success}/{len(descriptions)} 成功, {failed} 失败")
    print(f"输出: {output_file}")

    return 0 if success > 0 else 1


def main():
    parser = argparse.ArgumentParser(
        description='并行图片分析脚本（使用 Vision API）'
    )
    parser.add_argument(
        '--images-file',
        required=True,
        help='图片列表文件路径（_images.txt）'
    )
    parser.add_argument(
        '--output-dir',
        required=True,
        help='输出目录（descriptions.json 将写入此目录）'
    )
    parser.add_argument(
        '--concurrency',
        type=int,
        default=DEFAULT_CONCURRENCY,
        help=f'并行数（默认: {DEFAULT_CONCURRENCY}，最小: {MIN_CONCURRENCY}）'
    )
    parser.add_argument(
        '--max-retries',
        type=int,
        default=DEFAULT_MAX_RETRIES,
        help=f'单张图片最大重试次数（默认: {DEFAULT_MAX_RETRIES}）'
    )
    parser.add_argument(
        '--base-url',
        default=DEFAULT_BASE_URL,
        help=f'API base URL（默认: {DEFAULT_BASE_URL}）'
    )
    parser.add_argument(
        '--model',
        default=DEFAULT_MODEL,
        help=f'Vision 模型名称（默认: {DEFAULT_MODEL}）'
    )
    parser.add_argument(
        '--api-key-env',
        default=DEFAULT_API_KEY_ENV,
        help=f'API Key 环境变量名（默认: {DEFAULT_API_KEY_ENV}）'
    )

    args = parser.parse_args()

    # 运行异步主函数
    return asyncio.run(main_async(args))


if __name__ == '__main__':
    sys.exit(main())
