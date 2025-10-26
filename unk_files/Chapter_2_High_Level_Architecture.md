# V13 Adaptive Manual Trading Engine — Chapter 2: High-Level Architecture

## Architecture Overview

V13 operates as a hierarchical, modular intelligence system.  
Its architecture follows a clear command-and-control chain that mirrors military structure while remaining fully data-driven.

**Primary Layers**

- **CommanderBrain** – central orchestrator; gathers telemetry, fuses signals, and issues orders.  
- **Commanders** – tactical coordinators (Avengers, Assassins, etc.) translating doctrine into specific trade objectives.  
- **SquadCommanders** – manage small squads, distribute orders, and oversee local execution results.  
- **Soldiers** – execution agents carrying out orders under defined risk and timing rules.  
- **Analyzers & Risk Modules** – validate signals, monitor exposure, and feed feedback loops.  
- **Memory System** – stores session data, playbooks, and adaptive bias maps.  
- **Markets & Feeds** – interfaces for Alpaca, Binance Spot, and Binance Futures; provide market and news data.  
- **Monitors & API** – visualization, logging, and external command interface.

**Core Data Flow**

1. Feeds and analyzers produce Signals.  
2. CommanderBrain interprets signals, selects doctrines, and creates Orders.  
3. Orders propagate through Commanders → SquadCommanders → Soldiers.  
4. Soldiers return Reports with execution outcomes.  
5. CommanderBrain logs results into Memory and updates bias maps.

## Module Map

| Module | Purpose |
|:--|:--|
| **core_contracts** | Defines all dataclasses (Signal, Order, Report, MemoryNote) and protocol interfaces used system-wide. |
| **commander** | Houses CommanderBrain and MemoryUnit; handles signal fusion, order dispatch, and feedback logging. |
| **commanders** | Contains doctrine-based commanders (Avengers, Assassins) and the SquadCommander layer for tactical coordination. |
| **soldiers** | Implements execution agents and archetypes (Scout, Sniper, Runner, Shield); receives orders and produces reports. |
| **markets** | Abstract market connectors for Alpaca, Binance Spot, and Binance Futures; standardized order interface. |
| **analyzers** | Includes SignalValidator, RiskSentinel, PerformanceTracker, and DoctrineFeedbackLoop modules. |
| **memory** | Session and long-term storage of notes, playbooks, and brain snapshots. |
| **network** | Provides in-squad communication (Comms bus) and command network utilities. |
| **monitors** | Session Logger and Visual Monitor for real-time status tracking. |
| **api** | Flask control hub and dashboard endpoints. |
| **docs** | All official documentation and development manual chapters. |

This map serves as the foundation for module inter-dependency tracking and phase planning.

## Data Flow Description

The data flow inside V13 follows a closed adaptive loop designed for real-time feedback and doctrinal learning.

1. **Signal Generation:** Feeds and analyzers generate Signals based on tick data, news, and technical triggers.  
2. **Fusion & Interpretation:** CommanderBrain merges Signals, applies contextual filters, and produces actionable Orders.  
3. **Delegation:** Orders are sent to Commanders, then subdivided by SquadCommanders to their Soldiers.  
4. **Execution:** Soldiers act within the WarZone (simulation environment) using defined market connectors.  
5. **Reporting:** Soldiers return Reports summarizing outcome, slippage, and confidence metrics.  
6. **Learning:** CommanderBrain stores results and MemoryUnit updates playbooks, doctrines, and bias weights.

The loop repeats every tick, giving V13 continuous adaptive awareness.

## Component Interaction Summary

| Interaction | Description |
|:--|:--|
| **CommanderBrain ↔ Feeds** | Periodic polling of Feeds for new Signals. |
| **CommanderBrain ↔ Commanders** | Dispatch of Signals for tactical interpretation. |
| **Commanders ↔ SquadCommanders** | Delegation of Orders and receipt of SquadReports. |
| **SquadCommanders ↔ Soldiers** | Local mission control, equipment setup, and status monitoring. |
| **Soldiers ↔ Network.Comms** | Peer-to-peer communication for coordination and safety. |
| **CommanderBrain ↔ Memory** | Storage and retrieval of session notes and doctrine data. |
| **API ↔ CommanderBrain** | External control endpoints for simulation, monitoring, and testing. |

Together, these interactions define the operational nervous system of V13.
