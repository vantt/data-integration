# Diagram Patterns

Prefer Mermaid for workflow documentation.

## 1. Overview Flowchart

Use this to show the primary business path.

```mermaid
flowchart TD
    T["Trigger"] --> S1["Stage 1"]
    S1 --> S2["Stage 2"]
    S2 --> D{"Decision"}
    D -->|"PASS"| S3["Stage 3"]
    D -->|"FAIL"| R["Revise / Retry"]
```

## 2. Sequence Diagram

Use this to show actor handoffs and event emission.

```mermaid
sequenceDiagram
    participant U as Upstream
    participant O as Orchestrator
    participant A as Actor A
    participant B as Actor B

    U->>O: Trigger workflow
    O->>A: Dispatch task
    A-->>O: Output / signal
    O->>B: Dispatch review
    B-->>O: PASS / FAIL
```

## 3. State Diagram

Use this for loops, retries, and escalation logic.

```mermaid
stateDiagram-v2
    [*] --> Draft
    Draft --> Review
    Review --> Revise: fail
    Revise --> Review
    Review --> Approved: pass
    Review --> Escalated: round = 3
```

## 4. Data Flow

Use this for artifacts, zones, and outputs.

```mermaid
flowchart LR
    A["Input"] --> B["Run state"]
    B --> C["Intermediate artifacts"]
    C --> D["Final zone"]
    C --> E["Test zone"]
```
