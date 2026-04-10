# Mermaid Patterns Collection

Reusable diagram patterns with complete styling. Combine with [CHEATSHEET.md](CHEATSHEET.md) for syntax details.

## Flowchart Patterns

### Process with Error Handling

```mermaid
flowchart TD
    Start([Start]) --> Process[Process]
    Process --> Check{Success?}
    Check -->|Yes| Next[Continue]
    Check -->|No| Error[Handle Error]
    Error --> Retry{Retry?}
    Retry -->|Yes| Process
    Retry -->|No| Abort([Abort])

    style Start fill:#d3f9d8,stroke:#2f9e44,stroke-width:2px
    style Process fill:#e5dbff,stroke:#5f3dc4,stroke-width:2px
    style Check fill:#ffe3e3,stroke:#c92a2a,stroke-width:2px
    style Next fill:#c5f6fa,stroke:#0c8599,stroke-width:2px
    style Error fill:#ffe8cc,stroke:#d9480f,stroke-width:2px
    style Retry fill:#ffe3e3,stroke:#c92a2a,stroke-width:2px
    style Abort fill:#ffe3e3,stroke:#c92a2a,stroke-width:2px
```

### Three-Tier Architecture

```mermaid
flowchart TB
    subgraph frontend["Frontend Layer"]
        UI[User Interface]
        Display[Render Results]
    end

    subgraph backend["Backend Layer"]
        API[API Gateway]
        Logic[Business Logic]
        Auth[Authentication]
    end

    subgraph data["Data Layer"]
        DB[(Primary DB)]
        Cache[(Cache)]
        Queue[(Message Queue)]
    end

    UI --> API
    API --> Auth
    Auth --> Logic
    Logic --> DB
    Logic --> Cache
    Logic --> Queue
    DB --> Display

    style UI fill:#d3f9d8,stroke:#2f9e44,stroke-width:2px
    style Display fill:#c5f6fa,stroke:#0c8599,stroke-width:2px
    style API fill:#e5dbff,stroke:#5f3dc4,stroke-width:2px
    style Logic fill:#e5dbff,stroke:#5f3dc4,stroke-width:2px
    style Auth fill:#fff4e6,stroke:#e67700,stroke-width:2px
    style DB fill:#fff4e6,stroke:#e67700,stroke-width:2px
    style Cache fill:#fff4e6,stroke:#e67700,stroke-width:2px
    style Queue fill:#fff4e6,stroke:#e67700,stroke-width:2px
```

### AI Agent Workflow

```mermaid
flowchart TD
    Input[/"User Input"/] --> Perceive[① Perceive]
    Perceive --> Reason[② Reason]
    Reason --> Plan[③ Plan]
    Plan --> Act[④ Act]
    Act --> Output[/"Response"/]
    Output --> Evaluate{Goal Met?}
    Evaluate -->|No| Perceive
    Evaluate -->|Yes| Complete([Complete])

    style Input fill:#d3f9d8,stroke:#2f9e44,stroke-width:2px
    style Perceive fill:#e5dbff,stroke:#5f3dc4,stroke-width:2px
    style Reason fill:#e5dbff,stroke:#5f3dc4,stroke-width:2px
    style Plan fill:#ffe8cc,stroke:#d9480f,stroke-width:2px
    style Act fill:#ffe8cc,stroke:#d9480f,stroke-width:2px
    style Output fill:#c5f6fa,stroke:#0c8599,stroke-width:2px
    style Evaluate fill:#ffe3e3,stroke:#c92a2a,stroke-width:2px
    style Complete fill:#d3f9d8,stroke:#2f9e44,stroke-width:2px
```

### CI/CD Pipeline

```mermaid
flowchart LR
    Code[Code Push] --> Build[Build]
    Build --> Test[Test]
    Test --> Scan[Security Scan]
    Scan --> Deploy{Deploy?}
    Deploy -->|Yes| Staging[Staging]
    Staging --> Prod[Production]
    Deploy -->|No| Review[Code Review]
    Review --> Code

    style Code fill:#d3f9d8,stroke:#2f9e44,stroke-width:2px
    style Build fill:#e5dbff,stroke:#5f3dc4,stroke-width:2px
    style Test fill:#e5dbff,stroke:#5f3dc4,stroke-width:2px
    style Scan fill:#fff4e6,stroke:#e67700,stroke-width:2px
    style Deploy fill:#ffe3e3,stroke:#c92a2a,stroke-width:2px
    style Staging fill:#ffe8cc,stroke:#d9480f,stroke-width:2px
    style Prod fill:#c5f6fa,stroke:#0c8599,stroke-width:2px
    style Review fill:#f3d9fa,stroke:#862e9c,stroke-width:2px
```

## Sequence Patterns

### Authentication Flow

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant App
    participant Auth
    participant DB

    User->>App: Login request
    App->>+Auth: Validate credentials
    Auth->>+DB: Lookup user

    alt Valid
        DB-->>Auth: User found
        Auth->>Auth: Generate JWT
        Auth-->>-App: Token
        App-->>User: Login success
    else Invalid
        DB-->>Auth: Not found
        Auth-->>App: 401
        App-->>User: Login failed
    end
```

### Request with Retry

```mermaid
sequenceDiagram
    participant Client
    participant Service
    participant DB

    Client->>+Service: Request
    Service->>+DB: Query

    alt Success
        DB-->>Service: Data
        Service-->>Client: 200 OK
    else Failure
        DB-->>Service: Error
        Service->>Service: Retry (max 3)
        Service->>+DB: Query (retry)
        DB-->>-Service: Data
        Service-->>Client: 200 OK
    end
```

### Parallel Operations

```mermaid
sequenceDiagram
    participant API
    participant Email
    participant SMS
    participant Analytics

    API->>API: Process order

    par Notifications
        API->>Email: Send confirmation
        Email-->>API: Sent
    and
        API->>SMS: Send SMS
        SMS-->>API: Sent
    and
        API->>Analytics: Track event
        Analytics-->>API: Tracked
    end
```

## Class Diagram Patterns

### Repository Pattern

```mermaid
classDiagram
    class IRepository~T~ {
        <<interface>>
        +findById(id) T
        +save(entity: T)
        +delete(entity: T)
    }

    class UserRepository {
        -DbContext context
        +findByEmail(email) User
    }

    IRepository~User~ <|.. UserRepository
```

### Factory Pattern

```mermaid
classDiagram
    class ShapeFactory {
        +createShape(type) Shape
    }

    class Shape {
        <<abstract>>
        +draw()*
    }

    ShapeFactory ..> Shape : creates
    Shape <|-- Circle
    Shape <|-- Rectangle
    Shape <|-- Triangle
```

## ERD Patterns

### User-Centric Schema

```mermaid
erDiagram
    USER ||--o{ ORDER : places
    USER ||--o{ REVIEW : writes
    USER ||--o{ ADDRESS : has
    USER ||--|| PROFILE : has

    USER {
        uuid id PK
        string email UK
        string name
        timestamp created_at
    }

    ORDER {
        uuid id PK
        uuid user_id FK
        decimal total
        string status
    }
```

### Many-to-Many (Junction Table)

```mermaid
erDiagram
    STUDENT ||--o{ ENROLLMENT : has
    COURSE ||--o{ ENROLLMENT : includes

    STUDENT {
        uuid id PK
        varchar name
    }

    ENROLLMENT {
        uuid student_id FK PK
        uuid course_id FK PK
        date enrolled_date
        string grade
    }

    COURSE {
        uuid id PK
        varchar title
        int credits
    }
```

## Comparison Pattern

```mermaid
flowchart TB
    Title[Comparison: System A vs B]

    subgraph a["System A"]
        direction TB
        A1[Feature 1: Fast]
        A2[Feature 2: Limited]
        A3[Cost: High]
    end

    subgraph b["System B"]
        direction TB
        B1[Feature 1: Slow]
        B2[Feature 2: Extensive]
        B3[Cost: Low]
    end

    Title --> a
    Title --> b

    style Title fill:#e7f5ff,stroke:#1971c2,stroke-width:3px,color:#ffffff
    style A1 fill:#d3f9d8,stroke:#2f9e44,stroke-width:2px
    style A2 fill:#ffe3e3,stroke:#c92a2a,stroke-width:2px
    style A3 fill:#ffe8cc,stroke:#d9480f,stroke-width:2px
    style B1 fill:#ffe3e3,stroke:#c92a2a,stroke-width:2px
    style B2 fill:#d3f9d8,stroke:#2f9e44,stroke-width:2px
    style B3 fill:#d3f9d8,stroke:#2f9e44,stroke-width:2px
```

## Hub and Spoke Pattern

```mermaid
flowchart TB
    Hub[("Central Hub")]

    A[Service A] --> Hub
    B[Service B] --> Hub
    C[Service C] --> Hub
    D[Service D] --> Hub

    Hub --> E[("Database")]
    Hub --> F[/"External API"/]

    style Hub fill:#e7f5ff,stroke:#1971c2,stroke-width:3px
    style A fill:#d3f9d8,stroke:#2f9e44,stroke-width:2px
    style B fill:#d3f9d8,stroke:#2f9e44,stroke-width:2px
    style C fill:#d3f9d8,stroke:#2f9e44,stroke-width:2px
    style D fill:#d3f9d8,stroke:#2f9e44,stroke-width:2px
    style E fill:#fff4e6,stroke:#e67700,stroke-width:2px
    style F fill:#c5f6fa,stroke:#0c8599,stroke-width:2px
```

## Style Reference

```
# Semantic color mapping
Input/Start:    fill:#d3f9d8,stroke:#2f9e44  (Green)
Decision:       fill:#ffe3e3,stroke:#c92a2a  (Red)
Process:        fill:#e5dbff,stroke:#5f3dc4  (Purple)
Action:         fill:#ffe8cc,stroke:#d9480f  (Orange)
Output:         fill:#c5f6fa,stroke:#0c8599  (Cyan)
Storage:        fill:#fff4e6,stroke:#e67700  (Yellow)
Title/Hub:      fill:#e7f5ff,stroke:#1971c2  (Blue)
Learning:       fill:#f3d9fa,stroke:#862e9c  (Pink)
```
