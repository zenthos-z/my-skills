# Mermaid Syntax Cheatsheet

Quick reference for node shapes, arrows, and styling syntax.

## Node Shapes

| Shape | Syntax | Use Case |
|-------|--------|----------|
| Rectangle | `A[Text]` | Default, processes |
| Rounded | `B(Text)` | Start/end, soft actions |
| Stadium | `C([Text])` | Clear start/end markers |
| Circle | `D((Text))` | Connection points |
| Diamond | `E{Text?}` | Decisions, conditions |
| Hexagon | `F{{Text}}` | Special processes |
| Database | `G[(Text)]` | Data storage |
| Parallelogram | `H[/Text/]` | Input/output |
| Trapezoid | `I[/Text\]` | Manual input |
| Double circle | `J(((Text)))` | Start/end points |

## Arrow Types

| Type | Syntax | Meaning |
|------|--------|---------|
| Solid | `A --> B` | Primary flow |
| Dashed | `A -.-> B` | Optional, support |
| Thick | `A ==> B` | Emphasis |
| Invisible | `A ~~~ B` | Layout only |
| Bidirectional | `A <--> B` | Two-way |

**With labels:** `A -->|Label| B`

**Chaining:** `A --> B --> C` or `A --> B & C`

**Multi-target:** `A --> B & C & D`

## Styling Syntax

### Inline Style
```
style NodeID fill:#color,stroke:#color,stroke-width:2px
```

### Multiple Nodes
```
style A,B,C fill:#e5dbff,stroke:#5f3dc4
```

### Class-based (Reusable)
```
classDef process fill:#e5dbff,stroke:#5f3dc4,stroke-width:2px
classDef decision fill:#ffe3e3,stroke:#c92a2a,stroke-width:2px

A[Node]:::process
B{Choice}:::decision
```

### Style Properties

| Property | Values |
|----------|--------|
| `fill` | Background color |
| `stroke` | Border color |
| `stroke-width` | Border thickness (1px, 2px, 3px) |
| `color` | Text color |
| `stroke-dasharray` | Dashed border (e.g., 5 5) |

## Directions

```
flowchart TD    # Top-Down (vertical, default)
flowchart TB    # Top-Bottom (same as TD)
flowchart LR    # Left-Right (horizontal)
flowchart BT    # Bottom-Top
flowchart RL    # Right-Left
```

## Subgraph Syntax

### Basic
```
subgraph id["Display Name"]
    direction LR
    A --> B
end
```

### Nested (max 2 levels)
```
subgraph outer["Outer"]
    subgraph inner["Inner"]
        A --> B
    end
end
```

### Connecting Subgraphs
```
g1 -.-> g2        # By subgraph ID
A --> B           # By internal node
```

## Special Characters

| Character | Problem | Solution |
|-----------|---------|----------|
| Quotes `"` | Breaks syntax | Use `『』` or avoid |
| Parens `()` | May conflict | Use `「」` or avoid |
| `1. ` | List parsing | Use `①`, `(1)`, `Step 1:` |

## Node Text Guidelines

- **Line breaks:** `<br/>` only in circle nodes: `((Line1<br/>Line2))`
- **Length:** Keep under 50 characters
- **Spaces:** Use quotes: `["Text with spaces"]`

## Quick Patterns

### Decision
```
A -->|Yes| B
A -->|No| C
```

### Loop
```
A --> B --> C
C -.->|retry| A
```

### Parallel
```
A --> B & C & D
```

### Chain
```
A --> B --> C --> D
```
