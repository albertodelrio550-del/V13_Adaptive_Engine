# V13 Adaptive Manual Trading Engine — Chapter 3: Module Taxonomy & Packages

## Purpose
This chapter defines the organizational structure of the V13 codebase, grouping modules by function and responsibility.  
It ensures that all components remain cohesive, testable, and extensible as V13 evolves through future phases.

## Package Overview

| Package | Role |
|:--|:--|
| **core_contracts** | Central definitions of datatypes and interfaces shared across all subsystems. |
| **commander** | Orchestration brain and memory logic for coordination and adaptive learning. |
| **commanders** | Tactical units representing doctrines (Avengers, Assassins) and intermediate SquadCommanders. |
| **soldiers** | Individual execution agents with archetypes and squad composition logic. |
| **markets** | Broker connectors (Alpaca, Binance Spot, Binance Futures) and unified market interface. |
| **analyzers** | SignalValidator, RiskSentinel, PerformanceTracker, and other evaluators. |
| **memory** | Persistent storage for sessions, playbooks, and brain snapshots. |
| **network** | Communication layer for squad coordination and commander broadcasting. |
| **monitors** | Logging, visualization, and performance telemetry. |
| **api** | Flask service for control endpoints and monitoring dashboards. |
| **docs** | Technical manuals and internal documentation. |

## Naming Conventions

- **Snake case** for file and function names (e.g., `commander_brain.py`).  
- **Pascal case** for class names (e.g., `CommanderBrain`).  
- **Upper snake** for constants (e.g., `DEFAULT_RISK_CAP`).  
- Every package must contain `__init__.py` to declare it as importable.  
- Internal tests are placed inside each module under `/tests/` subfolders.

## Module Responsibilities

**core_contracts**  
Defines shared data structures (`Signal`, `Order`, `Report`, `MemoryNote`) and communication interfaces (`FeedPort`, `CommanderPort`, `SoldierPort`).  
Acts as the legal contract between all layers.

**commander**  
Hosts `CommanderBrain` and `SessionMemory`.  
Responsible for data fusion, doctrine selection, order distribution, and feedback storage.

**commanders**  
Implements doctrine-specific coordinators (`AvengersCommander`, `AssassinsCommander`) and the `SquadCommander` layer.  
Each commander interprets orders from the brain and manages tactical logic for its squads.

**soldiers**  
Contains execution archetypes (`Scout`, `Sniper`, `Runner`, `Shield`).  
Each soldier executes orders, reports results, and communicates with peers through `network.comms`.

**markets**  
Provides standardized market interfaces (`MarketInterface`).  
Implements connectors for Alpaca, Binance Spot, and Binance Futures—abstracted behind a common API.

**analyzers**  
Runs pre-trade and post-trade evaluation:  
`SignalValidator` (entry quality), `RiskSentinel` (exposure control), `PerformanceTracker` (session metrics), `DoctrineFeedbackLoop` (adaptive tuning).

**memory**  
Maintains persistent state—session logs, playbooks, brain snapshots, and doctrine metrics.

**network**  
Implements intra-squad communication and commander broadcast channels.

**monitors**  
Handles visualization, telemetry, and session reporting.  
Provides dashboards and log pipelines.

**api**  
Exposes control endpoints for simulation start/stop, status queries, and visualization feeds.

**docs**  
Contains development manuals, build logs, and future research notes.

## Inter-Package Dependencies

- `commander` imports datatypes from `core_contracts` and interacts with `commanders`, `analyzers`, and `memory`.  
- `commanders` depend on `core_contracts`, `soldiers`, and `network`.  
- `soldiers` depend on `core_contracts`, `markets`, and `network`.  
- `analyzers` may read from `memory` but never modify it directly.  
- `monitors` listen passively to outputs from `commander` and `soldiers`.  
- `api` communicates only with `commander` and `memory` layers.  
- Circular dependencies are prohibited—data must always flow downward, reports upward.


