<p align="center"><b>Quick Img</b></p>
<p align="center">快速图片生成技能 — 提示词直出、文档转信息图、批量抽卡</p>
<p align="center">
  <a href="https://www.dmxapi.cn"><img src="https://img.shields.io/badge/API-DMX-blue"></a>
  <img src="https://img.shields.io/badge/Model-Gemini_3.1_Flash_Image_Preview-green">
  <img src="https://img.shields.io/badge/Claude_Code-Skill-purple">
</p>

---

## TL;DR

| Feature | Benefit |
|---------|---------|
| 3 种使用模式 | Direct Prompt / Template / Refine，按需选择 |
| 14 种宽高比 | 覆盖小红书、Instagram、PPT 等场景 |
| 批量抽卡 | 同一 prompt 生成多张，API 随机产出不同结果 |
| 思源笔记集成 | 直接用笔记内容作为 prompt 生图 |
| 精炼模式 | 长内容先提炼，展示确认后再生成 |

---

## Quick Start

### 1. Install

```bash
# From monorepo (recommended)
git clone https://github.com/zenthos-z/my-skills.git
cp -r my-skills/quick-img ~/.claude/skills/
```

### 2. Configure

```bash
cp assets/.env.example assets/.env
# Edit: DMX_API_KEY=sk-your-api-key-here
# Get key: https://www.dmxapi.cn
```

### 3. Generate

```bash
# Direct Prompt（默认）
python scripts/generate_image.py --prompt "AI concept art" --ratio 16:9 --size 2K

# Template（文件转信息图）
python scripts/generate_image.py --input report.md --ratio 4:5 --size 2K

# Batch（抽卡 3 张）
python scripts/generate_image.py --prompt "landscape" --count 3
```

---

## Three Modes

### Mode 1: Direct Prompt（默认）

直接输入提示词生图。

```bash
python scripts/generate_image.py --prompt "futuristic city" --ratio 16:9 --size 2K
```

### Mode 2: Template

文件内容 + 生图模板 → 信息图。

```bash
python scripts/generate_image.py --input article.md --ratio 4:5 --size 2K
```

### Mode 3: Refine（精炼后生图）

长内容先提炼 → 展示精炼结果 → 确认后生成。Claude 行为层处理。

---

## Batch Generation（抽卡）

生成多张图片时，使用 `--count` 参数。同一 prompt，API 随机产出不同结果。

```bash
python scripts/generate_image.py --prompt "same prompt" --count 3
```

---

## Aspect Ratios

| Ratio | Use Case |
|-------|----------|
| 4:5 | Daily report, Instagram, 小红书 |
| 1:1 | Avatar, square post |
| 16:9 | PPT cover, video thumbnail |
| 9:16 | Phone wallpaper, Stories |
| 4:3 | Document illustration |

---

## Resolution

| Size | Pixels | Tokens | Best For |
|------|--------|--------|----------|
| 2K | 2048 | 1120 | Recommended, text-heavy infographics |
| 1K | 1024 | 1120 | Standard quality |
| 0.5K | 512 | 747 | Quick preview |
| 4K | 4096 | 2000 | Print quality |

---

## Commands Reference

```
python scripts/generate_image.py [options]

Mode:
  --prompt TEXT, -p         Direct prompt text
  --input PATH, -i          Source file path
  --template NAME, -t       Template name (default: 生图模板)

Image:
  --ratio RATIO             Aspect ratio (default: 4:5)
  --size SIZE               Resolution (default: 2K)
  --image-search            Enable image search
  --google-search           Enable Google search

Batch:
  --count N, -n             Number of images (default: 1)
  --save-prompts            Save prompts as .txt files

Output:
  --output-dir DIR, -o      Output directory
  --filename NAME, -f       Custom filename
  --dry-run                 Print prompt only
  --verbose, -v             Detailed logging
```

---

## Templates

| Template | File | Purpose |
|----------|------|---------|
| 生图模板 | `assets/templates/生图模板.txt` | General infographic wrapper |
| 海报模板 | `assets/templates/海报模板.txt` | Poster layout |
| 精炼提示词 | `assets/templates/精炼提示词模板.md` | Content refinement guide |

Custom templates: Create .txt files in assets/templates/, use {{content}} as placeholder.

---

## Limitations

| Limitation | Workaround |
|------------|------------|
| Chinese prompts may produce lower quality | Use English for key concepts |
| 2K/4K generation takes 10-30s | Use 1K for quick preview |

---

## Claude Integration

When user says "generate an image":
- Direct prompt → `python scripts/generate_image.py --prompt "..." --ratio X --size Y`
- File → `python scripts/generate_image.py --input <path> --ratio 4:5 --size 2K`
- Batch → `python scripts/generate_image.py --prompt "..." --count 3`
- Long content → Refine first, confirm, then generate
