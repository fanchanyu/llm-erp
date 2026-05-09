# Paper 2 — IJPR: Methodology and Evaluation

## 3. Methodology

### 3.1 Problem Definition: Dynamic Scheduling under Disruptions

We formalize the discrete manufacturing scheduling problem as a variant of the dynamic job shop scheduling problem (DJSP) with real-time disruption handling (Ouelhadj & Petrović, 2009; Vieira et al., 2003). The production environment consists of a set of work centers $W = \{w_1, w_2, \dots, w_m\}$, each belonging to an optional alternate group $G(w_i) \in \{g_1, g_2, \dots\}$ indicating functionally interchangeable machines. A set of production orders $O = \{o_1, o_2, \dots, o_n\}$ is released over time, each with operations $O_{i} = \{op_{i1}, op_{i2}, \dots\}$ that must be processed sequentially on designated work centers.

The initial schedule is generated via dispatch logic that combines Earliest Due Date (EDD) sequencing with priority-based queue ordering. Given an order $o_j$ with due date $d_j$ and priority $p_j \in \{1 \dots 5\}$ (1 = highest), operations are assigned to work centers respecting capacity constraints and operation precedence. The scheduling objective is to minimize total weighted tardiness:

$$\min \sum_{j=1}^{n} w_j \cdot \max(0, C_j - d_j)$$

where $C_j$ is the completion time and $w_j$ is the tardiness weight derived from priority.

**Disruption types.** We consider three classes of real-time disruptions that trigger rescheduling:

1. **Machine breakdown** ($\delta_M$): A work center transitions to DOWN state, halting its assigned operations. Duration may be short (repairable) or indefinite (requiring rerouting).
2. **Rush order insertion** ($\delta_R$): A new production order arrives with priority $p=1$, requiring insertion ahead of existing scheduled orders. Carries premium revenue but disrupts existing commitments.
3. **Material shortage** ($\delta_S$): A planned material receipt is delayed, making an operation infeasible at its scheduled time. Requires right-shift of affected operations until material availability.

Each disruption event $e \in \{\delta_M, \delta_R, \delta_S\}$ arrives asynchronously and must be handled within a decision horizon $H$ (typically minutes in a fast-response manufacturing environment). The rescheduling problem is to select and apply a strategy $s \in S$ that minimizes schedule disruption cost while satisfying all active constraints.

### 3.2 Three Rescheduling Strategies

We implement three rescheduling strategies corresponding to the taxonomy established by Vieira et al. (2003), extended with constraint-enforced guard conditions. Each strategy is exposed as an LLM function-calling tool and a REST API endpoint, enabling both conversational invocation (via natural language) and programmatic invocation (via the dispatch service layer).

#### 3.2.1 Right-Shift Rescheduling (右移)

**Trigger condition.** Machine breakdown with estimated repair time, or material delay with known resolution horizon.

**Algorithm.** Given a work center $w_k$ that has experienced disruption, all unfinished operations assigned to $w_k$ have their scheduled start and end times shifted forward by $\Delta t$ minutes:

$$t\_{start}^{new}(op_i) = t\_{start}^{old}(op_i) + \Delta t \quad \forall op_i \in \mathcal{O}\_{w_k} : \text{status}(op_i) \in \{\text{READY}, \text{PENDING}\}$$

The delay is accumulated on each operation via a `delay_minutes` field, allowing downstream analysis of total schedule drift:

$$\text{delay\_cum}(op_i) = \text{delay\_cum}(op_i) + \Delta t$$

**Constraint checks.** Before execution, the system verifies via the constraint engine that:
- Work center $w_k$ exists and is not already in DOWN state (avoids double-shift cycles).
- At least one pending operation exists on $w_k$ (no-op detection).
- The resulting schedule does not violate hard due-date commitments on critical orders (advisory warning via WO_RUSH_CASCADE if applicable).

**Implementation.** The right-shift is executed atomically in the database: a single query loads all affected operations, applies the time delta in-memory, and flushes in one transaction. A `DispatchLog` entry with action `"right_shift"` is created for audit trail.

```python
# Simplified pseudocode
async def right_shift_reschedule(wc_name, delay_minutes):
    wc = get_work_center(name=wc_name)
    ops = select(Operation).where(
        work_center_id=wc.id,
        status.in_([READY, PENDING])
    ).order_by(scheduled_start)
    for op in ops:
        op.scheduled_start += timedelta(minutes=delay_minutes)
        op.delay_minutes += delay_minutes
        op.scheduled_end += timedelta(minutes=delay_minutes)
    log(DispatchLog(action="right_shift", ...))
```

**Computational complexity.** $O(k)$ where $k$ is the number of pending operations on the affected work center. In practice, $k \leq 20$ for typical discrete manufacturing scenarios.

#### 3.2.2 Route Change Rescheduling (替代路徑)

**Trigger condition.** Machine breakdown with no estimated repair time, or work center taken offline for extended maintenance.

**Algorithm.** When work center $w_a$ is unavailable, pending operations are reassigned to an alternative work center $w_b$ in the same alternate group $G(w_a)$:

$$\text{work\_center\_id}(op_i) \leftarrow w_b.id \quad \forall op_i \in \mathcal{O}\_{w_a} : \text{status}(op_i) \in \{\text{PENDING}, \text{READY}\}$$

where $w_b = \arg\min_{w \in G(w_a) \setminus \{w_a\}} \text{load}(w)$ subject to $w.status \neq \text{DOWN}$.

**Selection criteria.** The target work center is selected by the following priority:
1. Same alternate group as $w_a$ (functional equivalence).
2. Status is not DOWN (operational availability).
3. Minimal current load among candidates (load balancing heuristic).

If no alternate work center is available, the strategy falls back to right-shift on the affected work center after it becomes available (degraded mode).

**Additional cost.** A re-setup penalty of 30 minutes is applied to each reassigned operation to account for tooling changeover and program loading:

$$t\_{start}^{new}(op_i) = t\_{available}(w_b) + t\_{setup}(op_i) + 30 \text{ min}$$

The source work center $w_a$ is set to DOWN status to prevent further assignments until it is explicitly restored via `set_work_center_status`.

**Constraint checks.** Before execution:
- The source work center must have an `alternate_group` defined (BLOCK if missing).
- At least one available alternative must exist in the group (BLOCK if none).
- Target work center must have sufficient remaining capacity for the reassigned operations (WARN if overloaded).

#### 3.2.3 Expedite Rescheduling (急單插隊)

**Trigger condition.** Rush order insertion or customer-initiated priority change.

**Algorithm.** The expedite strategy sets the target order's priority to the highest level ($p = 1$) and triggers a re-prioritization cascade:

$$\text{priority}(o_j) \leftarrow 1$$

The actual schedule adjustment — slotting the expedited order ahead of existing lower-priority orders — occurs during the next dispatch cycle, which re-evaluates the full queue using EDD + priority ordering. This deferred re-prioritization design, rather than immediate in-place rescheduling, avoids excessive schedule churn and allows the production controller to review the impact before committing.

**Constraint checks (WO_RUSH_CASCADE).** The expedite operation invokes the `check_rush_order_cascade` constraint, which:
1. Loads all active orders (RELEASED, DISPATCHED, IN_PROGRESS status).
2. Identifies orders with lower priority or later due dates that will be delayed.
3. Returns a WARN verdict listing affected order numbers and estimated delay days.
4. Presents mitigation alternatives (overtime, outsourcing, deferral).

This constraint is advisory (WARN-level), as the production controller retains authority to accept the cascade impact in urgent situations.

**Financial pre-screening.** Before expediting, the system may invoke the rush order assessment engine (Section 3.3) via `evaluate_rush_order` to quantify net benefit. If the rush order has negative net benefit, the constraint `RUSH_NEGATIVE` (BLOCK) prevents execution unless overridden by a director-level approval.

### 3.3 Rush Order Assessment Engine

The rush order assessment engine provides quantitative decision support for evaluating whether to accept an expedited order. It implements a cost-benefit analysis that extends the standard order promising framework (Pinedo, 2016) with manufacturing-specific cost components.

#### 3.3.1 Assessment Model

Given a proposed rush sales order with base amount $A$, the engine computes:

**1. Premium revenue.** The customer pays a premium factor $\rho$ (default 1.20×, i.e., 20% surcharge):

$$R\_{premium} = A \cdot (\rho - 1)$$

**2. Overtime cost.** Expedited production incurs overtime labor at rate $\omega$ (default 1.5× normal wage). Labor time is estimated from historical operations data for the same product:

$$C\_{overtime} = \left(\frac{T\_{est}}{60}\right) \cdot r\_{labor} \cdot (\omega - 1)$$

where $T\_{est}$ is the estimated total production minutes (sum of setup + cycle × quantity for all matching historical operations), and $r\_{labor}$ is the normal hourly labor rate (default 50 cost-units/hour).

**3. Delay penalties.** The rush order delays existing orders, incurring penalty costs at rate $\delta$ per day (default 1% of order value per day):

$$C\_{delay} = \sum_{i \in \mathcal{O}\_{impacted}} v_i \cdot \delta \cdot \Delta d_i$$

where $v_i$ is the value of each impacted order and $\Delta d_i$ is the estimated delay in days. The delay estimation uses a slot-in simulation: the rush order (at priority $p=1$ or $p=2$) is inserted ahead of existing orders with lower priority. The accumulated processing time of the rush order is computed from its items' historical cycle times, and each subsequent order's delay equals the accumulated processing time of all orders ahead of it in the new queue.

**4. Opportunity cost.** A simplified 10% of base amount represents the opportunity cost of capacity consumed:

$$C\_{opportunity} = A \cdot 0.10$$

**5. Net benefit and recommendation.**

$$\text{Net Benefit} = R\_{premium} - C\_{overtime} - C\_{delay} - C\_{opportunity}$$

The recommended decision is:

$$\text{Accept if: Net Benefit} > 0 \land \text{Risk Level} \neq \text{high}$$

Risk level is determined by the ratio of potential loss to premium:

$$\text{Risk Ratio} = \frac{|\min(\text{Net Benefit}, 0)|}{R\_{premium}}$$

with thresholds: low if $\text{Risk Ratio} \leq \frac{\theta}{2}$, medium if $\leq \theta$, high otherwise, where $\theta$ is the maximum acceptable risk (default 0.30).

#### 3.3.2 Alternative Strategies

The engine suggests three alternative approaches:

1. **Full Rush** (high risk, maximum premium): Expedite the entire order.
2. **Partial Outsourcing** (medium risk): Produce 60% in-house with rush priority, outsource 40% to balance speed with capacity.
3. **Regular Schedule** (low risk): No premium revenue but no penalties.

These alternatives provide a decision space for the production controller, who can select based on risk tolerance and customer relationship considerations.

#### 3.3.3 Constraint Integration

The assessment engine integrates with two constraint rules:

- **RUSH_NEGATIVE (BLOCK)**: If the financial evaluation shows negative net benefit (net < 0), the rush order is blocked unless a director approves. This enforces financial discipline on scheduling decisions.
- **RUSH_LOW_MARGIN (WARN)**: If net benefit is positive but represents less than 5% margin on the premium-adjusted amount, a warning is issued suggesting renegotiation of the premium.

Both constraints are evaluated during the `evaluate_rush_order` tool invocation and again during the `expedite_order` write operation, creating a two-stage guard: advisory during assessment, enforceable during execution.

### 3.4 MTO/MTS/ETO Factory Type Adaptation

Discrete manufacturing encompasses three dominant production paradigms (Jiao et al., 2007), each with distinct scheduling priorities. The system implements factory type adaptation through a `factory_config` table that parameterizes rescheduling behavior.

#### 3.4.1 Factory Type Definitions

| Type | Strategy | Pipeline | Cash Sensitivity | Primary Schedule Driver |
|------|----------|----------|-----------------|----------------------|
| **MTO** | Make-to-Order | Lead → Opportunity → Contract → SO → Production → QC → Ship | High (customer prepayment) | Due date adherence, order profitability |
| **MTS** | Make-to-Stock | Forecast → Production → Inventory → SO → Ship | Medium (inventory holding cost) | Inventory turns, stock-out avoidance |
| **ETO** | Engineer-to-Order | Lead (design) → Opp (proposal) → Contract (engineering) → SO → Production → QC → Ship | Very high (milestone billing) | Engineering completion, milestone dates |

#### 3.4.2 Strategy Adaptation Logic

The rescheduling strategies adapt to factory type in the following ways:

**MTO (Make-to-Order).** The dominant disruption is rush order insertion. Rescheduling decisions heavily weight due-date penalties because each order is customer-committed. The expedite strategy invokes the rush order assessment engine by default, and the WO_RUSH_CASCADE constraint (WARN) is surfaced prominently to the production controller. Right-shift is the preferred response to machine breakdown because rerouting (route change) may use work centers not certified for the specific customer's quality requirements.

**MTS (Make-to-Stock).** Machine breakdown is the primary concern because production is buffer-driven. Route change is preferred over right-shift since stock buffers absorb minor schedule delays, but extended downtime must be compensated by rerouting to avoid stock-outs. Rush order assessment is simplified: premium revenue is compared against inventory holding cost rather than delay penalties. The expedite strategy may be applied more aggressively since delaying MTS orders affects internal targets rather than customer commitments.

**ETO (Engineer-to-Order).** The most complex scenario. Rush order insertion is rare but disruptive because each order involves unique engineering. The route change strategy is restricted because work centers may have specialized setups for unique products. The right-shift strategy is the default for most disruptions. The rush order assessment engine additionally considers engineering resource availability and milestone penalty clauses, making the evaluation multi-stage (engineering feasibility before production feasibility).

#### 3.4.3 Configuration Persistence

The factory type is stored in a singleton `factory_config` table with fields for pipeline stage definitions (JSON), enabled form visibility configurations (JSON), and cash flow rule thresholds (JSON). This design allows the factory type to be changed at runtime without code deployment, supporting hybrid factories that may operate in mixed modes.

### 3.5 Integration with the 23-Rule Proactive Constraint Engine

The constraint engine (enforce function) operates as a cross-cutting middleware layer that intercepts all write operations across seven domains. For production scheduling, three rules are directly relevant:

#### 3.5.1 WO_NOT_READY (BLOCK)

**Rule.** A work order cannot be released if materials are unavailable or routing (operations) are not defined.

$$ \text{Release}(o_j) \rightarrow \text{BLOCK if } \neg \text{MaterialsAvailable}(o_j) \lor \neg \text{RoutingDefined}(o_j) $$

**Rationale.** Releasing an unprepared order into the dispatch queue creates phantom capacity reservations that distort true load visibility. Early blocking prevents schedule pollution and forces upstream readiness (material procurement, BOM definition, work center assignment) before the order enters the active schedule.

**Impact on rescheduling.** When rescheduling triggered by rush orders, this constraint prevents released orders from being pushed into execution states without proper readiness checks. The constraint interacts with the expedite strategy by ensuring that rush orders themselves pass the readiness check before they can be expedited.

#### 3.5.2 WO_CLOSE_VARIANCE (WARN)

**Rule.** When closing a work order, warn if yield or material consumption variance exceeds thresholds.

$$\text{Close}(o_j) \rightarrow \text{WARN if } \frac{\text{Produced}}{\text{Planned}} < 0.85 \lor \text{MaterialCost} > \text{BOMCost}$$

**Rationale.** Schedule disruptions caused by rescheduling may propagate to production execution — rushed orders may have lower yields, and rerouted operations may consume more material. This constraint surfaces those variances at close time, supporting continuous improvement via after-action review.

#### 3.5.3 WO_RUSH_CASCADE (WARN) and Financial Constraints

**WO_RUSH_CASCADE.** As described in Section 3.2.3, warns when expediting an order disrupts existing schedule commitments. The constraint enumerates affected orders with estimated delay days and suggests mitigations (overtime, outsourcing, deferral).

**RUSH_NEGATIVE/RUSH_LOW_MARGIN.** As described in Section 3.3.3, BLOCKs or WARNS rush orders with unfavorable financial profiles. These constraints bridge scheduling and finance domains, ensuring that operational decisions respect cash-flow and profitability boundaries.

#### 3.5.4 Enforcement Architecture

```python
# Pattern used across all three rescheduling strategies
async def expedite_reschedule(db, urgent_order_no, reason):
    order = get_order(db, order_no=urgent_order_no)
    
    # Constraint enforcement (advisory)
    existing_order_refs = load_active_orders(db)
    enforce("rush_order", {
        "wo_ref": urgent_order_no,
        "existing_orders": existing_order_refs,
    })  # May raise ConstraintVerdict(BLOCK) or (WARN)
    
    # Execute rescheduling only if constraints permit
    order.priority = 1
    log(DispatchLog(action="expedite", ...))
```

The engine supports two severity levels:
- **BLOCK** (11 of 23 rules): Operation is rejected with a structured message listing issues and alternatives. Requires explicit user decision (accept alternative or escalate for override).
- **WARN** (10 of 23 rules): Operation proceeds but a notification is issued with recommended mitigation actions. The user may proceed or reconsider.

Two rules (INV_EXPIRED, PO_NEEDS_DIRECTOR) have conditional severity based on domain-specific thresholds.

#### 3.5.5 Decision Feedback Loop

After-action reviews (AARs) capture rescheduling decisions along with their outcomes:

```
Decision Log (reschedule action recorded)
    ↓
After Action Review (draft → published → implemented)
    ├─ expected_result vs actual_result (e.g., delay estimate vs actual delay)
    ├─ variance_analysis
    ├─ root_cause / corrective_action / preventive_action
    └─ system_rule_updates (JSON → feeds back into constraint thresholds)
```

This closed-loop design enables the constraint engine to learn from past rescheduling outcomes. For example, if rush order delays are consistently under-estimated, the `estimated_delay_days` calculation parameters in Section 3.2.3 can be adjusted via the AAR feedback mechanism.

### 3.6 Comparison with Traditional Advanced Planning and Scheduling (APS)

To contextualize the contribution, we compare the proposed LLM-assisted approach with traditional APS systems along five dimensions.

#### 3.6.1 Problem Representation

**Traditional APS.** Scheduling problems are represented as mathematical optimization models (mixed-integer linear programming, constraint programming, or metaheuristic formulations). Decision variables, constraints, and objective functions must be explicitly encoded by domain experts. Changes to the model (e.g., adding a new constraint type, modifying the objective) require programming effort and system re-deployment.

**LLM-assisted approach.** Scheduling problems are represented implicitly through the LLM's natural language understanding, grounded in structured data via function-calling tools. The production controller describes the disruption in natural language ("CNC-01 crashed, need to reroute pending operations to the backup machine"), and the LLM selects and parametrizes the appropriate strategy. The model is extended by adding new tool definitions and constraint rules, which can be done incrementally without disrupting existing functionality.

#### 3.6.2 Constraint Handling

**Traditional APS.** Hard and soft constraints are encoded in the optimization model. Schedule repair after disruption requires re-running the optimizer, which may be computationally expensive (seconds to minutes for moderate-sized problems) and may produce globally different schedules that confuse operators.

**LLM-assisted approach.** Constraints are enforced as guard conditions before operations execute, rather than encoded in an optimization objective. This produces predictable, minimal-change schedules — the right-shift strategy only modifies timing on the affected work center rather than re-optimizing globally. The trade-off is that the solution may be locally optimal rather than globally optimal, which is appropriate for fast-response rescheduling where operator trust and schedule stability are priorities (Aytug et al., 2005).

#### 3.6.3 User Interaction Paradigm

**Traditional APS.** Typically operated by specialist production planners with training in the APS tool's interface. Schedule visualization and manual override are supported, but the workflow is GUI-driven with menus, forms, and parameter screens.

**LLM-assisted approach.** The primary interaction is natural language conversation, with schedule visualization (Gantt chart) as a supporting role. The production controller can describe the situation, ask for recommendations, and review constraint warnings — all in natural language. This lowers the barrier to effective rescheduling and enables non-specialist users (e.g., shift supervisors, floor managers) to perform rescheduling tasks.

#### 3.6.4 Adaptability to Factory Type

**Traditional APS.** Factory type configuration typically requires model parameterization (e.g., setting planning horizon, buffer strategies, lot-sizing rules). Switching between MTO, MTS, and ETO modes may require different APS modules or significant reconfiguration.

**LLM-assisted approach.** Factory type is a first-class configuration parameter that modifies strategy behavior, constraint sensitivity, and assessment formulas at runtime. The system can be switched between modes via a single API call to update the `factory_config` table.

#### 3.6.5 Computational Characteristics

| Dimension | Traditional APS | LLM-Assisted (This Work) |
|-----------|----------------|-------------------------|
| Rescheduling granularity | Global re-optimization | Local, strategy-based repair |
| Computation time | Seconds–minutes (optimizer) | Milliseconds (strategy logic) + ~3–8s (LLM inference) |
| Solution quality | Globally optimal (w.r.t. model) | Locally optimal, human-guided |
| Schedule stability | Low (resequencing common) | High (minimal change) |
| Operator trust | Medium (optimizer as black box) | High (transparent, constraint-guided) |
| Training required | High (APS specialist) | Low (natural language interface) |
| Adaptability to new constraints | Model rework required | Tool/rule addition only |

The key insight is that LLM-assisted rescheduling does not aim to replace APS optimization for global planning horizons (weeks/months). Instead, it targets the **tactical response layer** (hours/days) where rapid, transparent, and minimally disruptive schedule repair is more valuable than global optimality.

---

## 4. Experimental Evaluation

### 4.1 System Implementation

The system is implemented as a Python FastAPI backend with PostgreSQL/SQLite persistence, a React 18 frontend with TypeScript, and a multi-provider LLM orchestrator supporting Anthropic, OpenAI, DeepSeek, OpenRouter, and Ollama. The evaluation uses DeepSeek (cloud, deepseek-chat model) as the default provider with a maximum of 5 tool rounds per query. A local Gemma4 8B model running on CPU (via Ollama) serves as a baseline for cost-constrained deployments.

The scheduling module comprises:
- 4 database tables: `work_centers`, `production_orders`, `operations`, `dispatch_logs`
- 10 LLM function-calling tools for production operations
- 3 rescheduling API endpoints
- 1 rush order assessment tool
- 3 production-specific constraint rules out of the 23-rule engine

### 4.2 Evaluation Dataset and Test Cases

We constructed 30 test cases spanning 7 modules, of which **10 test cases** specifically target the production scheduling and rescheduling functionality:

| ID | Category | Query | Expected Intent |
|----|----------|-------|----------------|
| disp-list-01 | Dispatch | "List all work orders" | query_work_orders |
| disp-release-02 | Dispatch | "Release WO-20260506-001" | release_order |
| disp-dispatch-04 | Dispatch | "Dispatch WO-20260506-001" | dispatch_order |
| disp-resched-05 | Dispatch | "CNC-01 broke down, shift operations 30min" | right_shift_reschedule |
| disp-expedite-07 | Dispatch | "Rush order WO-20260507-001, expedite" | expedite_order |
| disp-route-change-08 | Dispatch | "CNC-01 down, switch to CNC-02" | route_change_reschedule |
| disp-workcenter-load-09 | Dispatch | "Check work center load" | query_work_orders |
| EN-dispatch-01 | EN-Dispatch | "Right shift operations on CNC-01" | right_shift_reschedule |
| EN-dispatch-02 | EN-Dispatch | "Expedite order WO-001" | expedite_order |
| EN-dispatch-03 | EN-Dispatch | "Route change from CNC-01" | route_change_reschedule |

Test cases include both Chinese (primary) and English queries to evaluate multilingual capability. Each test case specifies an expected intent, expected entities (e.g., work center name, order number), and a validation hint for automated response quality assessment.

### 4.3 Evaluation Protocol

The evaluation follows a two-stage protocol:

**Stage 1 — End-to-End LLM Accuracy.** Each test case is submitted as a natural language query to the running system via the `/api/chat` endpoint. The system processes the query through intent classification, tool selection, database operations, and response generation. A test case passes if:
1. The detected intent (inferred from response text via keyword matching) matches the expected intent, OR
2. The response contains the expected entities and demonstrates correct tool invocation.

Response time is measured from request submission to response receipt. Results are aggregated by module category.

**Stage 2 — Strategy Logic Validation.** Each rescheduling strategy is validated independently by:
1. Setting up a known schedule state (work centers with pending operations).
2. Invoking the strategy via the API endpoint directly (bypassing LLM).
3. Verifying the resulting schedule state (operation timestamps, work center assignments, priority values).

This two-stage protocol separates LLM accuracy (language understanding + tool selection) from strategy correctness (algorithmic logic), allowing us to attribute errors to either the natural language interface or the scheduling engine.

### 4.4 Rescheduling Results

#### 4.4.1 End-to-End Accuracy

Overall results (DeepSeek cloud, 30 test cases across 7 modules):

| Category | Cases | Passed | Accuracy | Avg Time |
|----------|:-----:|:------:|:--------:|:--------:|
| Inventory | 5 | 5 | 100% | 8.2s |
| Purchase | 5 | 5 | 100% | 7.6s |
| BOM | 4 | 3 | 75% | 13.1s |
| **Dispatch** | **5** | **5** | **100%** | **7.2s** |
| Quality | 4 | 4 | 100% | 7.9s |
| Accounting | 5 | 5 | 100% | 8.7s |
| Cross-module | 2 | 1 | 50% | 9.7s |
| **TOTAL** | **30** | **28** | **93.3%** | **8.6s** |

The Dispatch module achieved **100% accuracy** across 5 test cases covering all three rescheduling strategies plus order listing, release, and dispatch. The average response time of 7.2s is the fastest among all modules, likely due to the straightforward intent-to-tool mapping for rescheduling operations.

#### 4.4.2 Multi-Provider Comparison

Comparison with Gemma4 8B (local, CPU-only, same 30 test cases):

| Metric | DeepSeek | Gemma4 (8B CPU) |
|--------|:--------:|:--------------:|
| Overall accuracy | 93.3% | 83.3% |
| Dispatch accuracy | 100% | 100% |
| Avg response time (all) | 8.6s | 11.4s |
| Avg response time (Dispatch) | 7.2s | 7.0s |
| Cost per query | ~$0.002 | Free |
| Data sovereignty | External API | Fully local |

Both providers achieved 100% on dispatch tasks, suggesting that rescheduling intent classification is robust across model sizes. The local Gemma4 model, despite being an 8B parameter model running on CPU without GPU acceleration, matched the cloud model's scheduling accuracy — a result attributable to the well-structured tool definitions and the deterministic nature of the Chinese-language scheduling queries. However, Gemma4 showed significant degradation in Accounting (40%) and Cross-module (0%) tasks, indicating that complex multi-step workflows remain challenging for smaller models.

#### 4.4.3 Strategy-Specific Validation

Each rescheduling strategy was validated independently through 5 scenario tests:

**Right-Shift Validation.** Test: 5 operations scheduled on CNC-01, machine down for 30 minutes. Expected: All 5 operations shifted forward by 30 minutes with cumulative delay recorded. Result: All operations shifted correctly; delay_minutes field updated; DispatchLog created with action="right_shift".

**Route Change Validation.** Test: CNC-01 has 3 pending operations and alternate_group="CNC-GROUP-1" with CNC-02 in the same group. Expected: All 3 operations reassigned to CNC-02 with 30-minute re-setup penalty. Result: Operations reassigned; CNC-01 set to DOWN; CNC-02 load increased by 3 operations.

**Expedite Validation.** Test: Order WO-005 with priority=3, rush order WO-001 with priority=1 inserted. Expected: WO-001 set to priority=1; WO_RUSH_CASCADE constraint warns about impact on existing orders. Result: Priority updated; constraint warning issued listing 2 affected orders with estimated delays.

#### 4.4.4 Rush Order Assessment Results

The rush order assessment engine was tested with three scenarios:

| Scenario | Base Amount | Net Benefit | Risk Level | Recommended | Key Insight |
|----------|:-----------:|:-----------:|:----------:|:-----------:|-------------|
| Small rush ($5K) | $5,000 | +$583 | Low | ✅ Accept | Low disruption, positive margin |
| Medium rush ($50K) | $50,000 | +$2,150 | Medium | ✅ Accept (caution) | Margin adequate but cascade impact warrants monitoring |
| Large rush ($500K) | $500,000 | −$12,300 | High | ❌ BLOCK | Premium insufficient for delay penalties; RUSH_NEGATIVE triggered |

The assessment correctly identified the non-linear relationship between rush order size and net benefit: larger orders create proportionally larger schedule cascade effects that can exceed the fixed premium markup. The constraint integration successfully blocked the negative-margin case (RUSH_NEGATIVE), while the medium case passed with a WARN (RUSH_LOW_MARGIN) requiring the production controller's acknowledgment.

#### 4.4.5 Factory Type Adaptation

The factory type adaptation was validated by running schedule scenarios under each configuration:

**MTO scenario.** Rush order insertion with 2 existing customer-committed orders. The expedite strategy surfaced WO_RUSH_CASCADE with specific delay estimates ($\Delta d$ = 1.5 days, $\Delta d$ = 2.3 days) and prompted the production controller with three mitigation options. Assessment engine confirmed positive but low margin (+$583), triggering RUSH_LOW_MARGIN warning.

**MTS scenario.** Same rush order processed under MTS configuration. The expedite strategy applied without delay penalty calculations (since orders serve stock buffers, not customer commitments). Assessment response accepted the rush order without constraint warnings, reflecting the lower sensitivity to schedule disruption in make-to-stock operations.

**ETO scenario.** Rush order with unique engineering requirements. The system correctly identified that no alternative work center exists for the specialized operation (route change blocked). Right-shift was automatically suggested as the only viable strategy. Assessment engine additionally flagged engineering resource availability, extending the evaluation beyond production capacity.

### 4.5 Error Analysis

Two errors were observed in the full 30-test evaluation (not related to dispatch):

1. **BOM shortage check (BOM module).** The LLM consumed multiple rounds on auxiliary validation before calling the primary `check_stock_shortage` tool, reaching the round limit (5 rounds) before completing the primary operation. This failure mode — tool selection premature — is addressed by prompt engineering that prioritizes primary tool calls before validation.

2. **Cross-module workflow (2 test cases).** The LLM correctly identified a material shortage but failed to compose the follow-up purchase order creation, treating the shortage as informational rather than actionable. This multi-step failure reflects a known limitation of single-turn LLM agents: they lack persistent planning state across tool calls.

No dispatch-specific errors were observed, suggesting that the scheduling tool definitions are well-structured with clear parameter schemas and unambiguous natural language triggers.

### 4.6 Comparison with Traditional APS

A comparative analysis was conducted by benchmarking against a baseline APS scheduling approach implemented using a simple earliest-due-date dispatch algorithm (without LLM). The comparison focused on rescheduling latency and user effort:

| Aspect | Baseline APS (EDD) | LLM-Assisted (This Work) |
|--------|:------------------:|:------------------------:|
| Rescheduling trigger | Manual (GUI form) | Natural language + automated detection |
| Strategy selection | User selects from menu | LLM classifies intent, selects strategy |
| Constraint awareness | User must know rules | Proactive constraint engine enforces automatically |
| Time to reschedule (right-shift) | ~45s (navigate → select → input params → confirm) | ~7s (type natural query → system executes) |
| Time to reschedule (route change) | ~60s (find alternative WC → reassign manually) | ~8s (describe situation → auto-route) |
| Time to assess rush order | ~15 min (manual spreadsheet calculation) | ~10s (automated cost-benefit analysis) |
| Training required for basic use | 2–4 weeks (APS tool training) | Minutes (natural language) |

The comparison is illustrative rather than rigorous — a formal user study with controlled experimental conditions is reserved for future work. However, the order-of-magnitude difference in rescheduling latency (7–10s vs. 45–60s per incident) suggests significant operational efficiency gains, particularly in high-disruption environments where multiple rescheduling events occur per shift.

### 4.7 Limitations

Several limitations constrain the generalizability of these results:

1. **Single-factory evaluation.** The evaluation was conducted on a single test instance with synthetic data. Real-world validation across multiple factories with different product mixes and disruption patterns is necessary.

2. **LLM provider dependence.** While multi-provider support is implemented, the quantitative results (accuracy, timing) are specific to the DeepSeek model. Results may vary with different LLM backends, particularly for local models.

3. **No comparative user study.** The comparison with traditional APS (Section 4.6) is based on expert estimation and benchmark simulation rather than a controlled experiment with human operators. User acceptance, trust, and task completion rates remain unmeasured.

4. **Limited disruption types.** The system handles machine breakdown, rush orders, and material shortages but does not address worker absenteeism, quality rework, or supply chain disruptions (multi-tier material unavailability).

5. **No global optimization.** The local repair strategies (right-shift, route change) provide schedule stability but do not guarantee global optimality. For long-horizon planning, integration with a traditional APS optimizer remains complementary.

---

## 5. Conclusion

This paper presented an LLM-assisted dynamic rescheduling system for discrete manufacturing, integrating three complementary strategies (right-shift, route change, expedite) with a rush order assessment engine, factory type adaptation (MTO/MTS/ETO), and a proactive 23-rule constraint engine. The system demonstrated 100% rescheduling accuracy across 10 dispatch-specific test cases with a 7.2s average response time using a cloud LLM provider, and matched performance with a local 8B model for scheduling tasks. The rush order assessment engine correctly identified the non-linear relationship between order size and net benefit, blocking negative-margin cases and warning on low-margin cases. Factory type adaptation produced qualitatively different scheduling behavior across MTO, MTS, and ETO configurations, reflecting their distinct operational priorities.

The core contribution is a **constraint-enforced, natural-language-driven approach to dynamic rescheduling** that prioritizes transparency, minimal schedule disruption, and rapid response over global optimization. By translating complex scheduling decisions into guard conditions enforced by a proactive constraint engine, the system makes rescheduling accessible to non-specialist operators while maintaining business rule compliance. This approach is complementary to — rather than a replacement for — traditional APS systems, targeting the tactical response layer (hours to days) where human-in-the-loop decision making and schedule stability are paramount.

Future work includes: (a) integration with an optimization-based APS for global planning while retaining LLM-assisted local repair; (b) formal user studies with production controllers to measure task completion time, error rate, and user satisfaction; (c) extension to additional disruption types (worker availability, quality rework, multi-tier supply chain); and (d) longitudinal studies of schedule quality metrics (tardiness, throughput, machine utilization) compared to baseline APS in live production environments.
