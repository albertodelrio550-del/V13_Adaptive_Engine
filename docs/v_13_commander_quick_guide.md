# 🧭 V13 Commander Quick Guide
**Build:** V13_Stable_Release  
**Date:** 2025-10-20  
**Mode:** PAPER (default) | OFFLINE | REAL  

---

## ⚙️ System Overview

V13 is an **Adaptive Manual Trading Engine** integrating:
- **TelemetryFusion** → sentiment + volatility signal engine  
- **RiskSentinel** → adaptive risk kernel + drawdown control  
- **AdaptiveCycle** → phase logic (Assassin ⇄ Avenger)  
- **DoctrineFeedbackLoop** → tactical order generation  
- **PerformanceTracker** → profit ladder + performance logs  
- **CommanderMonitor** → unified operator console  
- **SessionAudit** → pre/post system integrity checks  

All systems synchronize through the **Commander Console**.

---

## 🧩 Launch Procedure

1. **Run Integrity Check**
   ```bash
   python core/V13_SessionAudit.py
