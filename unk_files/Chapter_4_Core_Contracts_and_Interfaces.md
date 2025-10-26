# V13 Adaptive Manual Trading Engine — Chapter 4: Core Contracts & Interfaces

---

## Dataclass Definitions

### Signal
Fields:
- id (UUID) — unique signal identifier  
- timestamp (datetime) — creation time  
- source (str) — originating analyzer or feed  
- payload (dict) — market or system data  
- confidence (float) — signal reliability (0–1)

Usage:
Immutable market observation used by analyzers and CommanderBrain.

### Order
Fields:
- id (UUID)  
- parent_signal (UUID)  
- direction (str) — "LONG" / "SHORT" / "EXIT"  
- size (float) — relative position sizing  
- metadata (dict) — execution hints (risk, priority)

Usage:
Instruction from CommanderBrain to Soldiers via Commanders.

### Report
Fields:
- id (UUID)  
- order_id (UUID)  
- status (str) — "EXECUTED", "CANCELLED", "SKIPPED"  
- pnl (float) — simulated profit / loss  
- latency (float) — simulated execution delay  
- notes (str)

Usage:
Returned by Soldiers to Commanders and Brain for evaluation.

### MemoryNote
Fields:
- id (UUID)  
- timestamp (datetime)  
- category (str) — "BIAS", "PERFORMANCE", "DOCTRINE"  
- content (str) — free-text or JSON payload  
- relevance (float)

Usage:
Persistent record of learning or state change stored by the Memory module.

---

## Interface Contracts

### FeedPort
Methods:
- `poll() -> Iterable[Signal]` — produce a list of fresh signals.  
- `describe() -> dict` — optional metadata (feed name, frequency).

### CommanderPort
Methods:
- `ingest(signals: Iterable[Signal]) -> None` — receive signals.  
- `decide() -> Iterable[Order]` — generate orders based on internal doctrine.  
- `review(reports: Iterable[Report]) -> None` — process outcomes and adapt.

### SoldierPort
Methods:
- `equip(config: dict) -> None` — configure trading parameters.  
- `execute(order: Order) -> Report` — carry out a simulated order.  
- `report() -> dict` — return current status or telemetry.

---

## Integration Rules

1. Every dataclass imports from `core_contracts` only.  
2. Interfaces are abstract — no business logic here.  
3. All cross-module communication must pass through these contracts.  
4. Version headers inside each contract define compatibility (e.g., `V13-CONTRACT-v1.0`).  
5. Any change to a contract requires an update in both documentation and codebase.

---
