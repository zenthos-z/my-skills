# Mermaid Error Prevention

Critical rules to avoid syntax errors. **Read this first when encountering issues.**

## Three Core Rules

### 1. List Syntax Conflict (Most Common)

Mermaid interprets `number. space` as Markdown ordered list.

```
❌ [1. Step]          → triggers "Unsupported markdown: list"
✅ [1.Step]           → remove space after period
✅ [① Step]           → use circled numbers ①②③④⑤⑥⑦⑧⑨⑩
✅ [Step 1: Name]     → use prefix format
✅ [(1) Step]         → use parentheses
```

### 2. Subgraph Naming

Subgraphs with spaces must use ID + display name format.

```
❌ subgraph AI Core
     A --> B
   end

✅ subgraph ai["AI Core"]
     A --> B
   end
```

### 3. Node Reference Rules

Always reference nodes by ID, never by display text.

```
# Define
A[Display Text A]
B["Display Text B"]

# Reference
✅ A --> B
❌ Display Text A --> Display Text B
```

## Special Characters

| Character | Problem | Solution |
|-----------|---------|----------|
| Quotes `"` | Breaks syntax | Use `『』` or avoid |
| Parens `()` | May conflict | Use `「」` or avoid |
| Curly `{}` | Reserved for subgraph/shape syntax | Use `「」` or remove |
| `number. space` | List parsing | Use `①`, `(1)`, or `1.Text` |
| Spaces in names | Reference issues | Use `id["Name"]` format |

## Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| `Unsupported markdown: list` | `1. Text` pattern | Use `① Text` or `1.Text` |
| `Expecting 'SEMI', 'NEWLINE'` | Invalid subgraph name | Use `subgraph id["Name"]` |
| `Unexpected character` | Unescaped special char | Use `『』` for quotes |
| Diagram doesn't render | Invalid connections | Check node IDs match definitions |

## Validation Checklist

Before finalizing:

- [ ] No `number. space` patterns (use `①`, `(1)`, or `Step 1:`)
- [ ] Subgraphs with spaces use `id["Name"]` format
- [ ] All node references use IDs, not display names
- [ ] Valid arrow syntax (`-->`, `-.->`, `==>`)
- [ ] Direction explicitly set (`TD`, `LR`, etc.)
- [ ] No unescaped quotes or parentheses in text

## Platform Notes

| Platform | Notes |
|----------|-------|
| GitHub | Good support, renders most syntax |
| Obsidian | Older version, more strict |
| Mermaid Live | Most up-to-date, best for testing |
