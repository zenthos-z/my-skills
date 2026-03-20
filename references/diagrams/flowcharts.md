# Flowcharts Reference

Flowcharts visualize processes, algorithms, decision trees, and user journeys.

## Basic Syntax

```
flowchart TD
    A --> B
```

**Directions:** `TD`/`TB` (top-bottom), `BT` (bottom-top), `LR` (left-right), `RL` (right-left)

## Subgraphs

```
flowchart TB
    subgraph id["Display Name"]
        direction TB
        A --> B
    end
```

**Nested subgraphs:** Keep to 2 levels maximum.

**Connecting:** Reference by ID (`g1 -.-> g2`) or connect internal nodes (`A --> B`)

## Styling

```
# Inline
style A fill:#d3f9d8,stroke:#2f9e44,stroke-width:2px

# Multiple nodes
style A,B,C fill:#d3f9d8,stroke:#2f9e44

# Class-based
classDef green fill:#d3f9d8,stroke:#2f9e44
A[Node]:::green
```

## Common Patterns

### Decision Tree

```mermaid
flowchart TD
    Start[Start] --> Decision{Condition?}
    Decision -->|Yes| PathA[Path A]
    Decision -->|No| PathB[Path B]
    PathA --> End[End]
    PathB --> End
```

### Loop Pattern

```mermaid
flowchart TD
    A[Initialize] --> B[Process]
    B --> C{Continue?}
    C -->|Yes| B
    C -->|No| D[Exit]
```

### Error Handling

```mermaid
flowchart TD
    A[Try operation] --> B{Success?}
    B -->|Yes| C[Continue]
    B -->|No| D[Handle error]
    D --> E{Retry?}
    E -->|Yes| A
    E -->|No| F[Abort]
```

### Swimlane

```mermaid
flowchart TB
    subgraph lane1["Process A"]
        A1[Step 1] --> A2[Step 2]
    end
    subgraph lane2["Process B"]
        B1[Step 3] --> B2[Step 4]
    end
    A2 --> B1
```

## Best Practices

1. **Meaningful labels** - Clear, action-oriented text
2. **Consistent shapes** - Same shape for same action types
3. **Diamond for decisions** - Standard convention
4. **Natural flow** - Top-to-bottom or left-to-right
5. **Start/end markers** - Use stadium shapes
6. **Group related steps** - Use subgraphs
7. **Color code** - Highlight different action types
8. **One process per diagram** - Keep focused
