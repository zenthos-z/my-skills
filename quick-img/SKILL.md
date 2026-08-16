---
name: quick-img
description: 快速图片生成技能，调用 Gemini 3.1 Flash Image 模型，支持网络搜索自动补参考图。支持 Direct Prompt / Template 两种模式，可批量生成。
usage: 有知识内容但不确定如何构图时调用（自动搜索参考图、代为构思画面结构）。不适用已有精确画面设计、文字密集的场景。
---

# Quick Img

快速图片生成工具，调用 Gemini 3.1 Flash Image 模型。

## 运行方式

```bash
# Direct Prompt 模式
python skills/quick-img/scripts/generate_image.py --prompt "你的提示词" --ratio 16:9

# Template 模式（源文件+模板）
python skills/quick-img/scripts/generate_image.py --input report.md --ratio 4:5

# 批量
python skills/quick-img/scripts/generate_image.py --prompt "prompt" --count 3

# 启用网络搜索
python skills/quick-img/scripts/generate_image.py --prompt "prompt" --google-search --image-search
```

## 快速参考

### 核心参数

| 参数 | 说明 | 默认 |
|------|------|------|
| `--prompt` / `-p` | 直接提示词 | - |
| `--input` / `-i` | 源文件（Template 模式） | - |
| `--ratio` | 宽高比 | 4:5 |
| `--size` | 分辨率 | 1K |
| `--count` / `-n` | 批量生成数量 | 1 |
| `--image-search` | 开启图片搜索 | off |
| `--google-search` | 开启网页搜索 | off |
| `--style-guide` / `-s` | 外部风格指南文件 | - |
| `--output-dir` / `-o` | 输出目录 | 源文件同目录或 `output/` |
| `--dry-run` | 仅打印提示词 | off |
| `--verbose` / `-v` | 详细日志 | off |

### 配置文件

- API Key: `skills/quick-img/assets/.env`（`DMX_API_KEY=***`）
- API 配置: `skills/quick-img/assets/config.json`
- 模板: `skills/quick-img/assets/templates/`

## 模型参数（可调）

通过 `assets/config.json` 可修改：

```json
{
  "api": {
    "base_url": "https://www.dmxapi.cn/v1/",
    "endpoint": "models/gemini-3.1-flash-image:generateContent"
  },
  "image_params": {
    "default_ratio": "4:5",
    "default_size": "1K",
    "default_image_search": false
  },
  "output": {
    "timestamp_format": "%Y%m%d-%H%M%S"
  }
}
```

底层 Gemini API 还支持 `temperature`、`topP`、`safetySettings` 等参数，当前脚本未暴露，有需要可加。
