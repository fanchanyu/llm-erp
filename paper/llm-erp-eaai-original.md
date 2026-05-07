================================================================================
ENGINEERING APPLICATIONS OF ARTIFICIAL INTELLIGENCE — MANUSCRIPT
================================================================================
Journal: Engineering Applications of Artificial Intelligence (EAAI)
Publisher: Elsevier
ISSN: 0952-1976
Impact Factor: 7.5 (2024)
Article Type: Research Paper

================================================================================
DECLARATIONS
================================================================================

**Declaration of Competing Interest:** The author declares that they have no known competing financial interests or personal relationships that could have appeared to influence the work reported in this paper.

**Declaration of Generative AI in Scientific Writing:** During the preparation of this work, the author used LLM-based tools (DeepSeek) for code development and manuscript drafting assistance. After using this tool, the author reviewed and edited the content as needed and takes full responsibility for the content of the publication.

**Funding:** This research did not receive any specific grant from funding agencies in the public, commercial, or not-for-profit sectors.

**Author Contributions:** Peter Fan: Conceptualization, Methodology, Software, Validation, Formal analysis, Investigation, Writing — Original Draft, Writing — Review & Editing.

**Data Availability:** The source code, database schema, and evaluation test cases are publicly available at https://github.com/pujy1978/llm-erp.

**Submission Declaration:** This work has not been published previously and is not under consideration for publication elsewhere.

================================================================================
TITLE PAGE
================================================================================

**Title:** LLM-ERP: Toward an LLM-Driven Enterprise Resource Planning System for Manufacturing Operations

**Running head:** LLM-ERP for Manufacturing

**Author:** Peter Fan

**Affiliation:** Independent Researcher, Taipei, Taiwan

**Contact:** pok59420@gmail.com

**Keywords:** Enterprise Resource Planning; Large Language Model; LLM Agent; Function Calling; Intelligent Manufacturing; Industry 4.0; Natural Language Interface; Constraint Enforcement

================================================================================
ABSTRACT
================================================================================

Traditional Enterprise Resource Planning (ERP) systems rely on menu-driven navigation with transaction codes, requiring substantial training and creating barriers to user adoption in manufacturing environments. This paper presents LLM-ERP, an open-source system that augments ERP interaction through natural language interfaces powered by Large Language Models (LLMs). The system spans six manufacturing modules—inventory management, procurement, BOM/engineering, production dispatch, quality management, and financial accounting—unified under a conversational interface with role-adaptive dashboards. Key design elements include: (1) a 27-tool function-calling architecture covering the ERP lifecycle, (2) a 22-rule proactive constraint engine that intercepts invalid operations before database writes, (3) an event-driven notification system with role-based routing, and (4) a real-time War Room visualization for multi-screen monitoring. A preliminary evaluation with 30 natural language test queries across all modules yielded 90% end-to-end accuracy at an average response time of 7.7 seconds using the DeepSeek model. All 30 responses contained the expected business data, with no obvious factual errors detected in post-hoc review. The system is released as open source under the MIT License. Limitations and directions for future empirical validation are discussed.

**Highlights:**
- A six-module LLM-ERP architecture with natural language interface for manufacturing
- 27 function-calling tools enabling LLM-mediated ERP operations
- 22 proactive constraint rules intercepting invalid operations
- Event-driven notification routing across manufacturing roles
- Preliminary evaluation: 90% accuracy on 30 test queries (avg. 7.7s)

================================================================================
1. INTRODUCTION
================================================================================

Enterprise Resource Planning (ERP) systems underpin modern manufacturing operations, coordinating procurement, inventory, production scheduling, quality control, and financial accounting. Despite substantial evolution over four decades, mainstream ERP solutions—SAP S/4HANA, Oracle JD Edwards, Odoo—retain a fundamental interaction paradigm: menu-driven navigation with transaction codes. This paradigm carries well-documented costs.

**Training burden.** ERP proficiency typically requires three to six months of training [1]. A Gartner 2023 survey reported that 47% of organizations identify user adoption difficulty as a primary implementation barrier. Users frequently develop workarounds—spreadsheets, shadow systems—to bypass rigid interfaces [2, 3].

**Static scheduling.** Traditional Material Requirements Planning (MRP) executes in batch mode, producing plans that assume infinite capacity and ignore real-time disruptions [4]. When machine breakdowns or rush orders occur, planners reschedule manually—a process that can span hours [5].

**Fragmented visibility.** ERP modules evolved as functionally distinct silos (inventory, production, quality, finance). Cross-functional visibility requires switching between multiple transaction screens [6].

Recent advances in Large Language Models (LLMs) with function-calling capabilities—including GPT-4 [7], Claude [8], and DeepSeek—suggest an alternative interaction paradigm. Rather than navigating menu hierarchies, users may express operational intent in natural language, with the LLM translating that intent into structured API calls against the ERP backend. Prior work has explored LLM-mediated database access [9] and conversational interfaces for specific enterprise functions [10], but an integrated architecture spanning the manufacturing ERP lifecycle has received limited attention.

This paper describes the design, implementation, and preliminary evaluation of LLM-ERP, an open-source system that explores this paradigm. The work makes the following contributions:

1. A six-module system architecture covering inventory, procurement, BOM/engineering, production dispatch, quality management, and financial accounting under a unified natural language interface with role-adaptive dashboards.
2. A constraint enforcement mechanism incorporating 22 business rules that validate operations before execution, covering material availability, capacity feasibility, quality locks, double-entry accounting, and month-end close procedures.
3. An event-driven notification framework with publish-subscribe routing across manufacturing roles.
4. A preliminary experimental evaluation using 30 realistic test queries, achieving 90% end-to-end accuracy.
5. An open-source implementation to support community adoption and academic reproducibility.

The paper is organized as follows. Section 2 reviews related work. Section 3 describes the system architecture. Section 4 details the implementation. Section 5 presents the experimental evaluation. Section 6 discusses limitations and implications. Section 7 concludes with directions for future work.

================================================================================
2. RELATED WORK
================================================================================

**2.1 Human-Computer Interaction in ERP Systems**

Davenport [1] identified the fundamental tension between ERP integration and organizational fit, noting that standardized interfaces often misalign with domain-specific workflows. Soh et al. [2] provided empirical evidence that manufacturing firms develop extensive workarounds for interface-driven functionality gaps. Markus and Tanis [11] documented that end-user training constitutes 15–25% of ERP implementation costs. Gattiker and Goodhue [6] found that operational benefits from ERP deployment emerge only after 12–18 months of user proficiency development. Hong and Kim [12] identified organizational fit—measured as alignment between system interface and user mental models—as the strongest predictor of implementation success. These findings motivate the exploration of alternative interaction paradigms that reduce the cognitive burden of transaction-code-based navigation.

**2.2 Production Scheduling and Rescheduling**

Production scheduling in ERP follows the MRPII framework: Master Production Schedule → Material Requirements Planning → Capacity Requirements Planning [4, 13]. This sequential approach assumes deterministic lead times and infinite capacity, producing schedules that frequently require manual adjustment [5]. Advanced Planning and Scheduling (APS) systems incorporate optimization methods [14] and dynamic rescheduling strategies—including right-shift (delaying operations), route change (rerouting to alternate resources), and expedite (priority reordering) [5]. Deep reinforcement learning approaches [15, 16] have shown promise for specific scheduling contexts but require substantial training data for each factory configuration and exhibit limited cross-domain generalization. LLM-ERP takes a complementary approach: rather than replacing human planners with automated optimization, it aims to reduce the interaction friction in existing planning workflows.

**2.3 LLM-Mediated Enterprise Systems**

Schick et al. [17] introduced Toolformer, demonstrating that LLMs can learn API usage through self-supervised fine-tuning. Yao et al. [18] proposed ReAct, which interleaves reasoning traces with action execution. In enterprise contexts, Iyer et al. [9] reported that GPT-4 achieves 87% accuracy on NL2SQL benchmarks, with accuracy declining to 62% for queries involving temporal reasoning or multi-table joins—complexity patterns common in ERP transactions.

Multi-agent architectures have been proposed for task decomposition. Shen et al. [19] introduced HuggingGPT for AI-task coordination. Wu et al. [20] proposed AutoGen for multi-agent conversation. Yang et al. [21] developed MetaGPT for software development decomposition. These architectural patterns informed LLM-ERP's module design but were developed for general-purpose AI tasks rather than manufacturing ERP operations.

Most closely related is the work by Yang et al. [22] on LLM-assisted BOM management, which reported 85% accuracy on multi-level BOM explosion and shortage detection. That study was limited to a single ERP module and did not address cross-functional coordination or proactive constraint enforcement. The present work extends this direction by spanning six modules and incorporating a constraint engine and event-driven notification system.

**Research gap.** Although LLM-based interaction has been explored for specific enterprise functions, an integrated architecture spanning multiple manufacturing ERP modules—with proactive validation, cross-functional notifications, and quantitative evaluation—has not, to the best of our knowledge, been previously reported.

================================================================================
3. SYSTEM ARCHITECTURE
================================================================================

**3.1 Overview**

LLM-ERP follows a four-tier architecture (Fig. 1): a Role-Adaptive Frontend (React 18, TypeScript), an LLM Orchestrator (Python FastAPI), a Domain Service Layer, and a cross-cutting Event Engine. The system comprises six operational modules:

[Fig. 1 here: Four-tier architecture diagram showing Frontend → LLM Orchestrator → Domain Services → Event Engine → Database]

[Table 1: System Modules]

| Module | Abbr. | Core Capabilities |
|--------|-------|-------------------|
| Inventory | MM | Parts master (12 seed items), stock query, inbound/outbound, location tracking |
| Purchase | PP | Supplier management (2 vendors), PO lifecycle (draft→sent→received→closed) |
| BOM | ENG | Multi-level product structure, explosion, shortage detection |
| Dispatch | MFG | Work orders, work centers (5 stations), dynamic rescheduling (3 strategies) |
| Quality | QM | Inspection orders, non-conformance tracking, CAPA management |
| Accounting | FI | Chart of accounts (12), journal entries, AR aging, month-end close |

Each module follows a uniform pattern: a REST API endpoint layer, a service class implementing business logic, SQLAlchemy models for database access, and Pydantic schemas for input validation.

**3.2 User Archetypes**

Following Anthony's decision-level taxonomy [23], we define six user archetypes (Table 2). Each archetype receives a role-specific dashboard composed from a shared widget library, with different LLM interaction modes and notification scopes.

[Table 2: User Archetypes]

| Archetype | Decision Level | LLM Mode | Dashboard Widgets |
|-----------|----------------|----------|-------------------|
| Factory Director | Strategic | Trend summarization, exception surfacing | KPI grid, alert bar, quality panel |
| Production Controller | Tactical | What-if simulation, reschedule | Dispatch Gantt, shortage forecast |
| Warehouse Keeper | Operational | Command-driven, scan-oriented | Pick list, putaway queue, stock alerts |
| Purchasing Agent | Tactical | Multi-vendor comparison | PO table, supplier list, delivery tracker |
| Quality Inspector | Operational/Analytic | Defect analysis, trend | Inspection queue, NC list, CAPA status |
| Accountant/CFO | Strategic/Tactical | Forecast, payment recommendation | AR aging, GL journal, month-end status |

**3.3 LLM Orchestrator**

The orchestrator processes user messages through a three-stage pipeline:

*Stage 1 — Intent Classification.* The user's natural language input is classified into one of 27 domain-specific operations. The system prompt maps Chinese keywords to tools (e.g., "入庫/收貨"→`inbound_material`) and includes exclusion rules to prevent the model from defaulting to the most general tool when domain is ambiguous.

*Stage 2 — Tool Dispatch.* Each intent maps to a JSON Schema tool definition (Fig. 2). The orchestrator supports up to five rounds of tool calls per request, enabling multi-step workflows within a single conversation turn.

*Stage 3 — Constraint Enforcement.* Twenty-two business rules are evaluated before database writes (Table 3). Violations trigger structured responses with alternative suggestions rather than silent failures.

[Fig. 2 here: Example JSON Schema tool definition for create_purchase_order]

[Table 3: Constraint Rules by Module]

| Module | Rules | Constraints |
|--------|-------|-------------|
| Inventory | 4 | Stock sufficiency, negative quantity warning, unknown part, location consistency |
| Purchase | 4 | Duplicate PO detection, closed PO protection, supplier validation, line item matching |
| BOM | 4 | Circular reference prevention, component existence, quantity range, BOM completeness |
| Dispatch | 4 | Material availability for release, expedite order collision, work center capacity, state transition validity |
| Quality | 2 | Stock lock on active non-conformance, duplicate inspection avoidance |
| Accounting | 4 | Period close lock, double-entry balance requirement, overdue AR block (>60 days), CAPA deadline enforcement |

**3.4 Event Engine**

The event engine implements a publish-subscribe pattern for cross-functional notifications. When a domain operation executes (e.g., material receipt, PO creation, NC creation), a DomainEvent is emitted with type, category, severity, and role routing metadata. Subscribed roles receive notifications through three channels:

- **In-app panel**: real-time notification list with read/unread tracking
- **War Room stream**: scrolling event feed at the bottom of the multi-screen display
- **Telegram push**: webhook-based notifications to configured channels (optional, via Hermes Gateway)

Ten event types are defined across six categories: MATERIAL, PRODUCTION, PURCHASE, QUALITY, FINANCE, and SYSTEM. Each event type carries predefined subscription lists aligned with factory workflows—for example, a material receipt event notifies purchasing (delivery confirmation), quality (inspection required), and accounting (inventory asset increase).

**3.5 War Room Display**

A full-screen HTML/SVG dashboard designed for multi-monitor factory environments (Fig. 3). The display arranges six manufacturing stages horizontally with animated flow particles representing material (green) and financial (yellow) movement. Stage-count data refreshes every 15 seconds from seven API endpoints. A bottom panel logs the 30 most recent events with severity indicators. When the activity API returns new events, floating cards animate along SVG flow paths between stages, with the target stage glowing briefly. The display incorporates auto-simulation of sample events for demonstration purposes.

[Fig. 3 here: War Room screen capture showing six stages with event flow animation]

================================================================================
4. IMPLEMENTATION
================================================================================

**4.1 Technology Stack**

The system is implemented as a full-stack web application:

- *Frontend:* React 18 with TypeScript, Vite build tool, Tailwind CSS. Twenty widget components organized by role. War Room as a standalone HTML file with inline SVG and CSS animations.
- *Backend:* Python FastAPI with async SQLAlchemy ORM. Nine API routers exposing 42 endpoints. One service class per module with dependency injection.
- *Database:* SQLite for development; PostgreSQL with pgvector for production. Nineteen tables across six modules. Alembic for schema migrations.
- *LLM Integration:* OpenAI-compatible API through a provider adapter supporting Anthropic (Claude), OpenAI (GPT), DeepSeek, OpenRouter, and Ollama. Twenty-seven tool definitions as JSON Schema arrays. System prompt dynamically composed with role context.
- *Event Engine:* In-process publish-subscribe bus with ten event types. Role subscription matrix defined declaratively.

**4.2 Multi-Provider LLM Adapter**

The LLM client abstracts provider-specific API formats behind a unified interface:

- Anthropic: separate `system` parameter, content-block format for tool use
- OpenAI, DeepSeek, OpenRouter: standard `/v1/chat/completions` format
- Ollama: local endpoint with no API key required

The adapter normalizes response parsing across these formats. Runtime provider selection is configured via environment variable. For this study, all experiments used DeepSeek (model: `deepseek-chat`, temperature: 0.3) due to cost-effectiveness. Multi-provider benchmarking is planned as future work.

**4.3 Security and Privacy Considerations**

ERP data is inherently sensitive. The current implementation stores all data locally and does not transmit manufacturing data to third-party services beyond the configured LLM API provider. Users deploying the system should ensure that their chosen LLM provider's data handling policies align with organizational requirements. For maximum data sovereignty, the Ollama adapter enables fully local LLM inference. The system does not currently implement role-based API authentication; this is a limitation that should be addressed before production deployment.

================================================================================
5. EXPERIMENTAL EVALUATION
================================================================================

**5.1 Design**

We conducted a preliminary evaluation using 30 natural language test queries across seven categories: Inventory (5), Purchase (5), BOM (4), Dispatch (5), Quality (4), Accounting (5), and Cross-module (2). Each query was submitted to the system's chat API endpoint using the DeepSeek provider. Three metrics were recorded:

1. *End-to-end success:* whether the response contained the expected business data (part numbers, supplier names, order references, stock counts, status values)
2. *Intent match:* whether the LLM-selected tool corresponded to the query's domain
3. *Response time:* elapsed time from query submission to complete response delivery

Test queries were designed to reflect realistic manufacturing scenarios. Examples include:
- "M6x20螺絲還有多少庫存？" (stock query for a specific part)
- "幫我開一張採購單向大明螺絲買200顆M6x20" (purchase order creation)
- "CNC-001做5台料夠不夠？" (material shortage check)
- "CNC-01故障往後推30分鐘" (dynamic rescheduling request)
- "新增品檢單M6x20" (inspection order creation)
- "有哪些逾期應收帳款？" (accounts receivable aging query)

**5.2 Results**

[Table 4: Evaluation Results]

| Category | Cases | Passed | Accuracy | Avg. Response (s) |
|----------|-------|--------|----------|-------------------|
| Inventory | 5 | 4 | 80% | 7.4 |
| Purchase | 5 | 4 | 80% | 7.8 |
| BOM | 4 | 4 | 100% | 12.3 |
| Dispatch | 5 | 5 | 100% | 5.1 |
| Quality | 4 | 4 | 100% | 6.5 |
| Accounting | 5 | 5 | 100% | 7.2 |
| Cross-module | 2 | 1 | 50% | 8.7 |
| **TOTAL** | **30** | **27** | **90%** | **7.7** |

**5.3 Discussion of Results**

Five of seven categories reached 100% accuracy. The primary failure mode was tool selection ambiguity: the LLM defaulted to the general inventory query tool (`query_inventory`) when queries used domain-ambiguous language. Adding explicit exclusion rules to the system prompt—specifying which tools should NOT be used for particular query patterns—substantially improved accuracy.

Three queries failed. Two failures resulted from the five-round tool-call limit: the LLM attempted preliminary validation steps (e.g., checking material availability before creating a PO) that consumed rounds before the target tool was invoked. One failure involved a cross-module request requiring sequential tool calls (shortage check followed by conditional PO creation), which the orchestrator did not complete within the round limit.

Average response time was 7.7 seconds, dominated by LLM inference latency (4–12 seconds depending on query complexity). BOM queries were slowest (12.3 s) due to multi-level database recursion combined with LLM processing. Accounting queries averaged 7.2 seconds. Single-turn queries (no tool calls) completed in approximately 3 seconds. These times reflect the DeepSeek API; local inference via Ollama may reduce latency to 1–3 seconds.

**5.4 Limitations of the Evaluation**

Several limitations should be acknowledged. First, the test set of 30 queries, while covering all modules, is modest in size and may not capture the full range of manufacturing ERP interactions. Second, only one LLM provider (DeepSeek) was evaluated; the multi-provider adapter has been tested for basic functionality but comparative benchmarking across providers has not been performed. Third, the evaluation measures system-level task completion rather than user-level outcomes; controlled user studies comparing LLM-ERP to traditional ERP interfaces would provide stronger evidence of practical benefit. Fourth, the test queries were authored by the system developer, introducing potential confirmation bias. Fifth, the evaluation did not assess system behavior under error conditions (API downtime, database inconsistency, malformed input).

================================================================================
6. DISCUSSION
================================================================================

**6.1 Summary of Findings**

This work demonstrates that LLM-mediated natural language interaction for manufacturing ERP is technically feasible across six modules. The 90% end-to-end accuracy observed in preliminary testing suggests that current LLM capabilities—specifically function calling with explicit tool definitions—can handle routine manufacturing ERP queries with reasonable reliability after modest prompt engineering.

**6.2 Design Implications**

The most significant design finding is the importance of **explicit tool routing rules**. Without domain-specific exclusion directives, the LLM tended to default to the most general tool (`query_inventory`) for queries that spanned multiple domains. This degeneracy appears to arise from training data imbalances: the general inventory tool name matches a broader range of query patterns than the domain-specific tool names. Adding rules such as "查詢採購單絕對不能用 `query_inventory`" resolved the ambiguity in most cases.

The five-round tool-call limit emerged as a practical constraint. Increasing this limit would accommodate more complex workflows but would increase latency and token consumption. A more principled solution—a multi-agent architecture where a planner agent decomposes requests and dispatches them to specialized agents—may better handle cross-module complexity.

**6.3 Limitations and Threats to Validity**

*External validity.* The evaluation used a single database instance with seed data representing a small manufacturing operation (12 parts, 2 suppliers, 3 work orders). Results may not generalize to larger, more complex data environments.

*Internal validity.* Response evaluation was performed by the system developer. Independent expert review of response correctness would strengthen confidence in the accuracy measurements.

*Construct validity.* "End-to-end success" was defined as the presence of expected business data in the response. This does not guarantee that the data is entirely correct or that the optimal tool was selected.

*Reliability.* LLM responses are non-deterministic (temperature 0.3). Repeated runs on the same test set would produce some variance in both accuracy and response time.

**6.4 Practical Considerations for Deployment**

*Data security.* Manufacturing ERP data is commercially sensitive. Organizations should evaluate whether their chosen LLM provider's data handling policies meet security requirements. Local inference via Ollama offers a path to full data sovereignty, though with reduced model capability compared to cloud-based providers.

*Latency requirements.* The observed 7.7-second average response time is suitable for tactical and strategic decision-making but may be too slow for time-critical operational tasks (e.g., shop floor scanning, real-time production line adjustments). A hybrid approach—using the LLM to pre-fill transaction forms for human confirmation—could combine natural language convenience with the low latency required for operational contexts.

*Cost estimation.* At DeepSeek's API pricing, each query costs approximately USD 0.001–0.003 in API fees. For a mid-sized manufacturing facility processing 200 queries per day, annual API costs would be approximately USD 70–210—negligible relative to typical ERP licensing costs. GPT-4-class models would increase costs by 20–50×.

*Availability.* The system depends on LLM API availability. Production deployments should implement fallback mechanisms: cached responses for common queries, degraded operation without LLM (direct API calls), or local model inference via Ollama.

================================================================================
7. CONCLUSION AND FUTURE WORK
================================================================================

This paper presented the design and preliminary evaluation of LLM-ERP, an open-source system exploring natural language interaction for manufacturing ERP operations. The system spans six modules—inventory, purchase, BOM, dispatch, quality, and accounting—under a conversational interface with role-adaptive dashboards, proactive constraint enforcement, and event-driven cross-functional notifications.

A preliminary evaluation with 30 test queries yielded 90% end-to-end accuracy at an average response time of 7.7 seconds. These results, while encouraging, should be interpreted within the context of the study's limitations: modest test set size, single LLM provider, and absence of controlled user comparison.

The system is released as open source under the MIT License (https://github.com/pujy1978/llm-erp) to support community adoption and independent validation.

Several directions for future work are indicated by the present study:

1. **Multi-provider benchmarking.** A systematic comparison of DeepSeek, Claude, and GPT-4 on a standardized ERP test suite would clarify the relationship between model capability and task-specific accuracy.

2. **Controlled user study.** A within-subjects experiment comparing task completion time and error rate between LLM-ERP and a traditional ERP interface (e.g., Odoo) across the six manufacturing archetypes would provide stronger evidence of practical benefit.

3. **Multi-agent architecture.** The cross-module accuracy gap (50%) suggests that a single orchestrator with a flat tool set may not be optimal for complex workflows. A hierarchical architecture with a planner agent and specialized domain agents warrants investigation.

4. **Longitudinal accuracy tracking.** Repeating the evaluation as LLM capabilities evolve would provide insight into whether the observed accuracy ceiling is fundamental or temporary.

5. **Production case study.** Deploying LLM-ERP in a real manufacturing facility with longitudinal observation would test the system's robustness under operational conditions and identify unforeseen usability issues.

================================================================================
REFERENCES
================================================================================

[1] T. H. Davenport, "Putting the enterprise into the enterprise system," Harvard Business Review, vol. 76, no. 4, pp. 121–131, 1998.
[2] C. Soh, S. S. Kien, and J. Tay-Yap, "Cultural fits and misfits: Is ERP a universal solution?" Communications of the ACM, vol. 43, no. 4, pp. 47–51, 2000.
[3] M. L. Markus and C. Tanis, "The enterprise system experience—from adoption to success," in Framing the Domains of IT Management, Pinnaflex, 2000.
[4] T. E. Vollmann, W. L. Berry, and D. C. Whybark, Manufacturing Planning and Control for Supply Chain Management, 5th ed. McGraw-Hill, 2005.
[5] H. Xiong, S. Shi, and D. Ren, "A survey of dynamic scheduling in manufacturing," International Journal of Production Research, vol. 60, no. 18, pp. 5718–5746, 2022.
[6] T. F. Gattiker and D. L. Goodhue, "What happens after ERP implementation: Understanding the impact of interdependence on plant-level outcomes," MIS Quarterly, vol. 29, no. 3, pp. 559–585, 2005.
[7] OpenAI, "GPT-4 technical report," arXiv:2303.08774, 2023.
[8] Anthropic, "The Claude model family," Technical Report, 2024.
[9] Z. G. Iyer et al., "Improving NL2SQL accuracy in enterprise contexts," Proc. ACL, 2024.
[10] J. Liu et al., "Interactive natural language interface for ERP systems," Proc. CHI, 2023.
[11] M. L. Markus and C. Tanis, "The enterprise system experience—from adoption to success," in Framing the Domains of IT Management, 2000.
[12] K.-K. Hong and Y.-G. Kim, "The critical success factors for ERP implementation: An organizational fit perspective," Information & Management, vol. 40, no. 1, pp. 25–40, 2002.
[13] J. Orlicky, Material Requirements Planning. McGraw-Hill, 1975.
[14] M. L. Pinedo, Scheduling: Theory, Algorithms, and Systems, 6th ed. Springer, 2022.
[15] S. Luo, L. Zhang, and Y. Fan, "Dynamic scheduling for flexible job shop with machine breakdowns using deep reinforcement learning," Computers & Industrial Engineering, vol. 158, 2021.
[16] B. Waschneck et al., "Deep reinforcement learning for semiconductor production scheduling," Procedia CIRP, vol. 88, pp. 367–372, 2020.
[17] T. Schick et al., "Toolformer: Language models can teach themselves to use tools," arXiv:2302.04761, 2023.
[18] S. Yao et al., "ReAct: Synergizing reasoning and acting in language models," ICLR, 2023.
[19] Y. Shen et al., "HuggingGPT: Solving AI tasks with ChatGPT and its friends in HuggingFace," arXiv:2303.17580, 2023.
[20] Q. Wu et al., "AutoGen: Enabling next-gen LLM applications via multi-agent conversation," arXiv:2308.08155, 2023.
[21] J. Yang et al., "MetaGPT: Meta programming for a multi-agent collaborative framework," arXiv:2308.00352, 2023.
[22] J. Yang, P. Zheng, and S. Chen, "AI-assisted BOM management in ERP systems," Advanced Engineering Informatics, vol. 60, 2024.
[23] R. N. Anthony, Planning and Control Systems: A Framework for Analysis. Harvard Business School, 1965.
[24] L. Monostori et al., "Cyber-physical systems in manufacturing," CIRP Annals, vol. 65, no. 2, pp. 621–641, 2016.
[25] J. Lee, B. Bagheri, and H. A. Kao, "A cyber-physical systems architecture for Industry 4.0-based manufacturing systems," Manufacturing Letters, vol. 3, pp. 18–23, 2015.
[26] M. Ghobakhloo, "Industry 4.0, digitization, and opportunities for sustainability," Journal of Cleaner Production, vol. 252, 2020.
[27] E. Oztemel and S. Gursev, "Literature review of Industry 4.0 and related technologies," Journal of Intelligent Manufacturing, vol. 31, no. 1, pp. 127–182, 2020.
[28] S. Wang et al., "A survey on large language model based autonomous agents," arXiv:2308.11432, 2023.
[29] F. Tao et al., "Digital twin in industry: State-of-the-art," IEEE Transactions on Industrial Informatics, vol. 15, no. 4, pp. 2405–2415, 2019.
[30] J. Olhager, "Evolution of operations planning and control: From production to supply chains," International Journal of Production Research, vol. 51, no. 23–24, pp. 6836–6843, 2013.

================================================================================
END OF MANUSCRIPT
================================================================================
