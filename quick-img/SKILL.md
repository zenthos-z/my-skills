---
name: quick-img
description: |
  Quick Img - 通过 API 快速生成高质量图片（DMX Gemini 3.1 Flash Image Preview）。

  使用场景:
  - 快速提示词生图（Direct Prompt）
  - Markdown 文档转信息图
  - 思源笔记内容生图
  - 长内容精炼后生图（先展示精炼结果）
  - 批量抽卡（同一提示词生成多张）

  触发词: banana生图, 图片生成, 生图, generate image
---

# Quick Img

通过 DMX API 快速生成高质量图片。

## 首次使用设置

### Step 1: 配置 API Key
1. 复制配置文件:
   cp assets/.env.example assets/.env
2. 编辑 assets/.env，填入 API Key:
   DMX_API_KEY=sk-your-api-key-here
3. 获取 API Key: https://www.dmxapi.cn
4. 验证: python scripts/generate_image.py --prompt "test" --dry-run

### Step 2: 选择使用模式
| 模式 | 命令 | 适用场景 |
|------|------|----------|
| Direct Prompt | --prompt "提示词" | 自由创作、快速生图（默认） |
| Template | --input file.md | Markdown文档转信息图 |
| Refine（精炼） | Claude 行为层 | 内容过长时先提炼，确认后再生成 |

默认使用 Direct Prompt 模式，无需额外配置。

### Step 3: 配置提示词模板
两个关键模板位于 assets/templates/：

| 模板 | 文件 | 作用 |
|------|------|------|
| 生图模板 | assets/templates/生图模板.txt | Template 模式的提示词包装（含风格要求） |
| 精炼提示词 | assets/templates/精炼提示词模板.md | Refine 模式的内容提炼指南 |

修改方式: 直接编辑对应文件即可。模板使用 {{content}} 作为内容占位符。

## 三种使用模式

### Mode 1: Direct Prompt（默认）
直接输入提示词生图。最常用，零配置。

python scripts/generate_image.py --prompt "提示词" --ratio 4:5 --size 2K

适用场景：自由创作、概念图、快速生图、思源笔记内容生图。

### Mode 2: Template
读取文件内容，套用「生图模板」后生成信息图。

python scripts/generate_image.py --input article.md --ratio 4:5 --size 2K

适用场景：Markdown 文档转配图。

### Mode 3: Refine（精炼后生图）
当内容过长或需要提炼时使用。流程由 Claude 在行为层完成：
1. 检查调用方是否提供了精炼模板路径
   - **有外部精炼模板**（如其他技能提供）→ 直接使用该模板精炼
   - **无外部精炼模板** → **询问用户**选择：使用默认精炼模板 / 手动提供精炼要求 / 跳过精炼直接生图
2. Claude 按模板指引提炼内容
3. 先展示精炼结果给用户确认
4. 用户确认后，调用 --prompt 生图

不涉及新的 CLI 参数，纯 Claude 行为。

## 批量生成（抽卡）

重要: 当用户要求生成多张图片时，Claude 必须:
1. 构建一个提示词
2. 使用 --count N 参数
3. 绝对不要 拆分或修改提示词
4. 绝对不要 多次调用脚本

正确做法:
python scripts/generate_image.py --prompt "同一个提示词" --count 3

错误做法（不要这样做）:
python scripts/generate_image.py --prompt "提示词变体1"
python scripts/generate_image.py --prompt "提示词变体2"

每张图片使用完全相同的提示词，由 API 的随机性产生不同结果。

## 思源笔记生图

用户说"用这篇笔记生图"时的工作流：
1. 通过 SiYuan MCP 读取笔记内容:
   mcp__siyuan__search(action="fulltext", query="笔记标题")
   mcp__siyuan__document(action="get_doc", id="文档ID")
2. 根据内容长度选择模式:
   - 短内容 → Direct Prompt: --prompt "笔记内容"
   - 长内容 → Refine 模式（先展示精炼结果）
3. 调用脚本生图

## 参数速查

### 宽高比（常用）
| 比例 | 适用场景 |
|------|----------|
| 4:5 | 信息图、小红书、Instagram |
| 1:1 | 头像、方形帖子 |
| 16:9 | PPT封面、视频封面 |
| 9:16 | 手机壁纸、Stories |
| 4:3 | 文档插图 |

### 分辨率
| 尺寸 | Token消耗 | 适用场景 |
|------|-----------|----------|
| 2K | 1120 | 推荐，高清信息图 |
| 1K | 1120 | 标准质量 |
| 0.5K | 747 | 快速预览 |
| 4K | 2000 | 印刷级别 |

### 完整参数
模式选择:
  --prompt TEXT, -p         直接输入提示词（Direct Prompt）
  --input PATH, -i          源文件路径（Template 模式）
  --template NAME, -t       模板名称（默认: 生图模板）

图片参数:
  --ratio RATIO             宽高比（默认: 4:5）
  --size SIZE               分辨率（默认: 2K）
  --image-search            启用图片搜索参考
  --google-search           启用 Google 搜索

批量生成:
  --count N, -n             生成数量（默认: 1）
  --save-prompts            保存提示词为 .txt 文件

输出控制:
  --output-dir DIR, -o      输出目录（Direct Prompt 模式）
  --filename NAME, -f       自定义文件名
  --style-guide PATH, -s    外部风格指南文件路径（追加到提示词末尾）
  --style-guide PATH, -s    外部风格指南文件路径（追加到提示词末尾）
  --json PATH, -j           JSON 配置文件路径（覆盖其他参数）
  --dry-run                 仅打印提示词，不调用 API
  --verbose, -v             显示详细日志

## 外部技能调用协议

其他 Claude Code 技能可通过 Skill 工具调用 quick-img。

### 调用方式

```
Skill(skill: "quick-img", args: "<JSON文件路径>")
```

收到 args 后，Claude 直接透传给脚本：

```bash
python scripts/generate_image.py --json <args>
```

**Claude 不解析 JSON 内容**，所有解析和验证由脚本完成。

### JSON 文件格式

```json
{
  "prompt": "提示词内容（必填）",
  "style_guide": "风格指南文件路径（空或不填 = 不追加风格）",
  "count": 1,
  "ratio": "4:5",
  "size": "2K",
  "output_dir": "输出目录路径",
  "filename": "自定义文件名",
  "image_search": false,
  "google_search": false
}
```

**必填**：`prompt`（不能为空）

**风格行为**：
- `style_guide` 有值（文件路径）→ 读取文件追加到 prompt 末尾
- `style_guide` 为空/省略 → 纯净 prompt 直发 API，不追加任何风格

## Claude 内部调用指南

### 用户说"帮我画一张图" / "生图"
1. 确认用户想要的图片内容
2. 构建 prompt
3. python scripts/generate_image.py --prompt "..." --ratio X --size Y

### 用户说"把这篇文章转成图"
1. 确认文件路径
2. python scripts/generate_image.py --input <path> --ratio 4:5 --size 2K

### 用户说"用这篇笔记生图"
1. 通过 SiYuan MCP 读取笔记内容
2. 短内容 → --prompt "笔记内容"
3. 长内容 → 先精炼展示，确认后 --prompt "精炼内容"

### 用户说"生成3张" / "抽卡"
1. 构建一个 prompt
2. python scripts/generate_image.py --prompt "..." --count 3
3. 不要修改提示词，不要多次调用

### 用户说"内容太长了"
1. 读取 assets/templates/精炼提示词模板.md
2. 按模板提炼内容
3. 展示精炼结果
4. 用户确认后 → --prompt "精炼内容" 生图
