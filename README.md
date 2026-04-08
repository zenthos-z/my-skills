<p align="center">
  <b>DMX Image Generator</b>
</p>

<p align="center">
  将 Markdown 日报、文档一键转化为高质量信息图 / 海报 / 配图
</p>

<p align="center">
  <a href="https://www.dmxapi.cn"><img src="https://img.shields.io/badge/API-DMX-blue" alt="DMX API"></a>
  <img src="https://img.shields.io/badge/Model-Gemini_3.1_Flash_Image_Preview-green" alt="Model">
  <img src="https://img.shields.io/badge/Claude_Code-Skill-purple" alt="Claude Code Skill">
</p>

---

## TL;DR

**Problem:** 写完日报 / 周报后，还需要手动做配图，费时且设计质量不稳定。

**Solution:** 一条命令，Claude 读取内容 → 提炼精华 → 调用 DMX API 生成专业信息图。

| Feature | Benefit |
|---------|---------|
| 4 种工作模式 | 从极简拼接 到 高级变量注入，按需选择 |
| 14 种宽高比 | 覆盖小红书、Instagram、PPT、手机壁纸等场景 |
| 模板系统 | 自带日报/海报/信息图模板，支持自定义 |
| 批量生成 | 一次生成多张，自动命名保存 |
| Claude 提炼模式 | AI 先提炼核心内容，再生成，效果最佳 |

---

## Quick Start

### 1. Install

```bash
npx skills add <owner/repo>@dmx-image-gen
```

### 2. Configure API Key

```bash
# Copy the example env file
cp assets/.env.example assets/.env

# Edit with your DMX API Key
# DMX_API_KEY=sk-your-api-key-here
```

> Get your API Key from [DMX API](https://www.dmxapi.cn)

### 3. Generate

```bash
# Daily report → infographic (recommended)
python scripts/generate_image.py \
  --input reports/daily/2026-03-24.md \
  --ratio 4:5 --size 2K

# Free creation
python scripts/generate_image.py \
  --prompt "AI concept art, futuristic city" \
  --ratio 16:9 --size 2K
```

---

## Four Modes

### Mode A: Simple (Default)

Template + source file content → image. Zero config.

```bash
python scripts/generate_image.py --input report.md --ratio 4:5 --size 2K
```

### Mode A+: Simple + Claude Refined (Recommended)

Claude reads and distills the source, then generates with the refined content.

```bash
python scripts/generate_image.py \
  --input report.md \
  --refined-content "Distilled key insights..."
```

**Workflow:**
1. Claude reads `assets/templates/refine_for_image.md`
2. Extracts core insights, data, conclusions
3. Passes refined content via `--refined-content`

### Mode B: Advanced (Variable Injection)

Fine-grained control with template variables.

```bash
python scripts/generate_image.py \
  --input report.md --advanced \
  --var date="2026-03-24" \
  --var summary="Discussion on AI memory mechanisms"
```

**Template syntax:**

| Syntax | Description | Example |
|--------|-------------|---------|
| `{{content}}` | Source content placeholder | Used in all modes |
| `{{var}}` | Required variable | `{{date}}` |
| `{{var\|default}}` | Variable with default | `{{style\|modern}}` |
| `{{#var}}...{{/var}}` | Conditional block | Renders only if var is set |

### Mode C: Manual (Free Prompt)

Direct prompt input, no template processing.

```bash
python scripts/generate_image.py \
  --prompt "AI concept diagram" --ratio 16:9 --size 2K
```

**Mode priority:** `--prompt` > `--refined-content` > `--advanced` > Simple (default)

---

## Aspect Ratios

### Popular

| Ratio | Use Case | Resolution |
|-------|----------|------------|
| **4:5** | Daily report, Instagram, 小红书 | 1024x1280 |
| **1:1** | Avatar, square post | 1024x1024 |
| **16:9** | PPT cover, video thumbnail | 1024x576 |
| **9:16** | Phone wallpaper, Stories | 576x1024 |
| **4:3** | Document illustration | 1024x768 |

### Resolution Tiers

| Size | Pixels | Tokens | Best For |
|------|--------|--------|----------|
| **2K** | 2048 | 1120 | Daily report with text (recommended) |
| **1K** | 1024 | 1120 | Standard quality, best value |
| **0.5K** | 512 | 747 | Quick preview |
| **4K** | 4096 | 2000 | Print quality |

---

## Commands Reference

```
python scripts/generate_image.py [options]

Mode:
  --input PATH, -i          Source file path
  --prompt TEXT, -p         Direct prompt text
  --refined-content TEXT    Claude-refined content
  --advanced, -a            Enable variable injection
  --template NAME, -t       Template name (default: default)

Image:
  --ratio RATIO             Aspect ratio (default: 4:5)
  --size SIZE               Resolution (default: 2K)
  --image-search            Enable image search reference
  --google-search           Enable Google search

Batch:
  --count N, -n             Number of images (default: 1)
  --save-prompts            Save prompts as .txt files

Output:
  --output-dir DIR, -o      Output directory (manual mode)
  --filename NAME, -f       Custom filename
  --dry-run                 Print prompt only, no API call
  --verbose, -v             Detailed logging
```

---

## Templates

Located in `assets/templates/`:

| Template | Purpose | Mode |
|----------|---------|------|
| `default.txt` | General infographic | Simple |
| `daily_infographic.txt` | Daily report infographic (Morandi palette) | Simple |
| `daily_report.txt` | Daily report with variables | Advanced |
| `poster.txt` | General poster | Advanced |
| `refine_for_image.md` | AI refinement prompt | Mode A+ |

**Custom templates:** Create `.txt` files in `templates/` using `{{content}}` as placeholder.

---

## Output Rules

- **Naming:** Auto-detected from content + timestamp
  - Daily report → `日报_20260324_143052.png`
  - Poster → `海报_20260324_143052.png`
  - Generic → `生成图片_20260324_143052.png`
- **Location:** Same directory as source file (Simple/Advanced modes); `--output-dir` for Manual mode

---

## Limitations

| Limitation | Workaround |
|------------|------------|
| Chinese prompts may produce slightly lower quality | Use English for key concepts |
| 2K/4K generation takes 10-30s | Use 1K for quick preview |
| Content too long may dilute results | Use Mode A+ (Claude refined) |
| Max 14 aspect ratios | Cover all common social media formats |

---

## Claude Integration Guide

When user says "convert daily report to image", Claude should:

1. **Choose mode:** Typically Mode A+ (Simple + Claude Refined)
2. **Read refinement template:** `assets/templates/refine_for_image.md`
3. **Distill source:** Extract key points, conclusions, data
4. **Execute:**
   ```bash
   python scripts/generate_image.py \
     --input report.md \
     --refined-content "Refined content..." \
     --ratio 4:5 --size 2K
   ```

---

## References

| Document | Content |
|----------|---------|
| `references/parameters.md` | Full parameter reference (14 ratios, token costs, API features) |
| `docs/prompt-flowchart.md` | Prompt assembly mechanism with flowchart |
