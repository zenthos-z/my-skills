---
name: dmx-image-gen
description: |
  DMX Image Generator - 通过 DMX API 的 Gemini 3.1 Flash Image Preview 模型生成高质量图片。

  使用场景:
  - 日报/周报转配图
  - Markdown文档生成信息图
  - 快速图片生成

  触发词: banana生图, 图片生成, 日报转图片
---

# DMX Image Generator

**设计理念**: 极简模式为默认（模板+源文件直接拼接），可选高级模式（变量注入）。

## 快速开始

```bash
# 极简模式（默认）- 日报转图片
python scripts/generate_image.py \
  --input reports/daily/2026-03-24.md \
  --ratio 4:5 --size 2K

# 极简模式 + 批量生成 3 张 + 保存提示词
python scripts/generate_image.py \
  --input reports/daily/2026-03-24.md \
  --ratio 4:5 --size 2K --count 3 --save-prompts

# 手动模式 - 自由创作
python scripts/generate_image.py \
  --prompt "AI概念图" --ratio 16:9 --size 2K
```

## 核心配置（常用）

配置文件: `assets/config.json`

### 推荐宽高比

| 比例 | 适用场景 |
|------|----------|
| `4:5` | **日报推荐**、小红书、Instagram竖版 |
| `1:1` | 头像、方形帖子 |
| `16:9` | PPT封面、视频封面 |
| `9:16` | 手机壁纸、Stories |

### 推荐分辨率

| 尺寸 | Token消耗 | 适用场景 |
|------|-----------|----------|
| `2K` | 1120 | **日报推荐**，高清信息图 |
| `1K` | 1120 | 标准质量，性价比高 |
| `0.5K` | 747 | 快速预览 |
| `4K` | 2000 | 印刷级别 |

## 三种使用模式

### 模式A: 极简模式（默认）

模板前缀 + 源文件内容 → 生成图片

```bash
python scripts/generate_image.py --input report.md --ratio 4:5 --size 2K
```

### 模式A+: 极简+Claude提炼（推荐）

Claude先提炼精华，再生成图片。

```bash
python scripts/generate_image.py \
  --input report.md \
  --refined-content "提炼后的核心内容..."
```

**工作流程:**
1. Claude读取 `assets/templates/refine_for_image.md`
2. Claude提炼原文，提取认知差、实战工作流
3. 传入 `--refined-content` 生成图片

### 模式B: 高级模式（需显式开启）

```bash
python scripts/generate_image.py --input report.md --advanced \
  --var date="2026-03-24" \
  --var summary="讨论AI记忆机制"
```

**模板语法:**
- `{{content}}` - 源文件内容占位
- `{{var}}` - 必填变量
- `{{var|default}}` - 带默认值的变量
- `{{#var}}...{{/var}}` - 条件块

### 模式C: 手动模式

```bash
python scripts/generate_image.py --prompt "AI概念图" --ratio 16:9 --size 2K
```

## 命令行参数

```
模式选择:
  --input PATH, -i          源文件路径
  --prompt TEXT, -p         直接输入提示词
  --refined-content TEXT    Claude提炼后的内容
  --advanced, -a            启用高级变量注入
  --template NAME, -t       模板名称 (默认: default)

图片参数:
  --ratio RATIO             宽高比 (默认: 4:5)
  --size SIZE               分辨率 (默认: 2K)
  --image-search            启用图片搜索
  --google-search           启用 Google 搜索

批量生成:
  --count N, -n             生成数量 (默认: 1)
  --save-prompts            保存提示词为 .txt 文件

输出控制:
  --output-dir DIR, -o      输出目录（手动模式）
  --filename NAME, -f       自定义文件名
  --dry-run                 仅打印提示词
  --verbose, -v             显示详细日志
```

## API Key 设置

1. 复制 `assets/.env.example` 为 `assets/.env`
2. 填入你的 DMX API Key:
   ```
   DMX_API_KEY=sk-your-api-key-here
   ```

## 输出规则

1. **文件名**: 基于内容自动识别 + 时间戳
   - 日报: `日报_20260324_143052.png`
   - 海报: `海报_20260324_143052.png`
   - 通用: `生成图片_20260324_143052.png`

2. **保存位置**:
   - 极简/高级模式：源文件同目录
   - 手动模式：通过 `--output-dir` 指定（默认: `./output`）

## 模板文件

位置: `assets/templates/`

| 模板 | 用途 | 模式 |
|------|------|------|
| `default.txt` | 默认极简模板 | 极简模式 |
| `daily_infographic.txt` | 日报信息图专用 | 极简模式 |
| `daily_report.txt` | 日报高级模板 | 高级模式 |
| `poster.txt` | 通用海报 | 高级模式 |
| `refine_for_image.md` | AI提炼提示词 | 模式A+ |

**自定义模板**: 在 templates 目录创建 `.txt` 文件，使用 `{{content}}` 占位符。

## 参考资料

| 文档 | 内容 |
|------|------|
| `references/parameters.md` | 完整参数参考（14种比例、Token消耗、API功能） |

## Claude 内部调用指南

当用户说"将日报转成图片"时，Claude应该：

1. **确定模式**: 通常使用 模式A+（极简+Claude提炼）
2. **读取提炼模板**: `assets/templates/refine_for_image.md`
3. **提炼原文**: 提取核心要点、结论、数据
4. **调用脚本**:
   ```bash
   python scripts/generate_image.py \
     --input report.md \
     --refined-content "提炼内容..." \
     --ratio 4:5 --size 2K
   ```

## 注意事项

- **极简模式**是默认推荐，无需理解模板语法
- 需要精细控制时才使用 `--advanced` 开启高级模式
- 中文提示词效果可能略逊于英文，关键概念可用英文
- 2K 和 4K 分辨率会消耗更多令牌
- 生成时间：1K 约 3-8 秒，2K/4K 约 10-30 秒
