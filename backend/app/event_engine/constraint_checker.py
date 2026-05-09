"""Proactive constraint checker — validates operations before execution.

Each write operation (CREATE, UPDATE, DELETE) is intercepted by the
constraint checker, which evaluates business rules and returns a list
of warnings, alternatives, or blocks before the operation proceeds.

This is the core "proactive AI" pattern: instead of blindly executing,
the system surfaces risks and alternatives for the user to consider.

FULL CONSTRAINT MATRIX:
┌──────────────────────────────────────┬──────────┬──────────┐
│ Domain       │ Constraint                     │ Type     │
├──────────────────────────────────────┼──────────┼──────────┤
│ Inventory    │ Negative stock prevention       │ BLOCK    │
│ Inventory    │ FIFO expiration enforcement     │ BLOCK    │
│ Inventory    │ Safety stock warning            │ WARN     │
│ Inventory    │ Slow-moving / dormant alert     │ INFO     │
│ Inventory    │ Cycle count variance approval   │ BLOCK    │
│ Purchase     │ Over-receipt cap (PO +10%)      │ BLOCK    │
│ Purchase     │ Two-stage approval by amount    │ WARN     │
│ Purchase     │ Supplier score lock (<3.0)      │ BLOCK    │
│ Purchase     │ Auto-penalty on late delivery   │ INFO     │
│ BOM          │ Circular reference detection    │ BLOCK    │
│ BOM          │ Active BOM edit protection      │ BLOCK    │
│ Production   │ Material availability at release │ BLOCK    │
│ Production   │ WO close reconciliation         │ WARN     │
│ Production   │ Rush order cascade impact       │ WARN     │
│ Quality      │ QC-hold material blocking       │ BLOCK    │
│ Quality      │ NC cascade lock                 │ BLOCK    │
│ Quality      │ Recurring defect → MRB          │ WARN     │
│ Finance      │ Month-end closing lock          │ BLOCK    │
│ Finance      │ Auto double-entry enforcement   │ WARN     │
│ Finance      │ AR overdue → shipment block     │ BLOCK    │
└──────────────────────────────────────┴──────────┴──────────┘
"""
from __future__ import annotations
import logging
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Optional, Callable

logger = logging.getLogger(__name__)


class CheckResult(Enum):
    PASS = "pass"
    WARN = "warning"
    BLOCK = "block"


@dataclass
class ConstraintVerdict:
    result: CheckResult
    message: str
    code: str = ""                 # machine-readable error code
    details: str = ""
    alternatives: List[str] = field(default_factory=list)
    required_approval_role: Optional[str] = None
    affected_entities: List[str] = field(default_factory=list)  # WOs, POs, etc.


# ═══════════════════════════════════════════════════════════════════
# INVENTORY CONSTRAINTS
# ═══════════════════════════════════════════════════════════════════

def check_negative_stock(item: str, current_qty: float,
                          requested_qty: float) -> ConstraintVerdict:
    """BLOCK if issuing more than available."""
    remaining = current_qty - requested_qty
    if remaining < 0:
        short = -remaining
        return ConstraintVerdict(
            result=CheckResult.BLOCK,
            code="INV_NEGATIVE_STOCK",
            message=f"庫存不足：{item} 現有 {current_qty}，需 {requested_qty}，短缺 {short}",
            alternatives=[
                f"採購補貨 {short} 單位",
                f"以替代料取代（需工程核准）",
                f"調撥其他倉庫庫存",
            ],
        )
    return ConstraintVerdict(result=CheckResult.PASS, message="")


def check_safety_stock(item: str, current_qty: float,
                        requested_qty: float,
                        safety_stock: float = 0) -> ConstraintVerdict:
    """WARN if remaining stock falls below safety level."""
    remaining = current_qty - requested_qty
    if safety_stock > 0 and remaining < safety_stock:
        return ConstraintVerdict(
            result=CheckResult.WARN,
            code="INV_BELOW_SAFETY",
            message=f"發出後庫存將降至 {remaining}（安全水位 {safety_stock}）",
            details=f"{item}: {current_qty} → {remaining}",
            alternatives=[f"僅發放 {int(max(0, current_qty - safety_stock))}，保留安全庫存"],
        )
    if remaining < current_qty * 0.2:  # fallback: warn if below 20%
        return ConstraintVerdict(
            result=CheckResult.WARN,
            code="INV_BELOW_20PCT",
            message=f"發出後庫存將降至 {remaining}（低於現有量20%）",
            alternatives=[f"僅發放 {int(current_qty * 0.8)} 以保留緩衝"],
        )
    return ConstraintVerdict(result=CheckResult.PASS, message="")


def check_expiry(item: str, lot: Optional[str],
                  expiry_date: Optional[str]) -> ConstraintVerdict:
    """BLOCK if lot is expired."""
    if not expiry_date:
        return ConstraintVerdict(result=CheckResult.PASS, message="")
    try:
        exp = datetime.fromisoformat(expiry_date)
        if exp < datetime.utcnow():
            return ConstraintVerdict(
                result=CheckResult.BLOCK,
                code="INV_EXPIRED",
                message=f"批號 {lot} 已於 {expiry_date} 到期，不可發料",
                alternatives=[
                    f"退回供應商",
                    f"申請報廢（需品管核准）",
                    f"申請特採（需廠長核准）",
                ],
            )
        # Warn if within 30 days
        if exp < datetime.utcnow() + timedelta(days=30):
            return ConstraintVerdict(
                result=CheckResult.WARN,
                code="INV_EXPIRING_SOON",
                message=f"批號 {lot} 將於 {expiry_date} 到期（剩 { (exp - datetime.utcnow()).days } 天）",
            )
    except (ValueError, TypeError):
        pass
    return ConstraintVerdict(result=CheckResult.PASS, message="")


def check_dormant_stock(item: str, last_movement_days: int,
                         current_qty: float) -> ConstraintVerdict:
    """WARN if stock hasn't moved in 90+ days (dormant/slow-moving)."""
    if current_qty <= 0:
        return ConstraintVerdict(result=CheckResult.PASS, message="")
    if last_movement_days >= 365:
        return ConstraintVerdict(
            result=CheckResult.WARN,
            code="INV_DORMANT_1Y",
            message=f"{item} 庫存 {current_qty} 已超過1年未異動（{last_movement_days}天），建議檢視是否為呆料",
            alternatives=[
                f"標記為呆滯料，提報處置方案",
                f"降價促銷 / 轉單使用",
                f"申請報廢（需廠長核准）",
            ],
        )
    if last_movement_days >= 90:
        return ConstraintVerdict(
            result=CheckResult.WARN,
            code="INV_SLOW_MOVING",
            message=f"{item} 庫存 {current_qty} 已 {last_movement_days} 天未異動（超過90天），列為慢動料",
            alternatives=[f"標記為慢動料，納入定期檢視清單"],
        )
    return ConstraintVerdict(result=CheckResult.PASS, message="")


def check_cycle_count_variance(item: str, recorded_qty: float,
                                 actual_qty: float) -> ConstraintVerdict:
    """BLOCK adjustment if variance > 5% without approval."""
    if recorded_qty == 0:
        return ConstraintVerdict(result=CheckResult.PASS, message="")
    variance_pct = abs(actual_qty - recorded_qty) / recorded_qty * 100
    if variance_pct > 5:
        return ConstraintVerdict(
            result=CheckResult.BLOCK,
            code="INV_COUNT_VARIANCE",
            message=f"盤點差異 {variance_pct:.1f}% — 帳面 {recorded_qty}，實盤 {actual_qty}，差異 {actual_qty - recorded_qty}",
            details="超過5%容差，需主管核准才能調整",
            alternatives=[
                f"重新盤點確認",
                f"申請調整（需主管核准）",
                f"標記為異常，啟動調查",
            ],
            required_approval_role="director" if variance_pct > 10 else "production",
        )
    return ConstraintVerdict(result=CheckResult.PASS, message="")


# ═══════════════════════════════════════════════════════════════════
# PURCHASE CONSTRAINTS
# ═══════════════════════════════════════════════════════════════════

def check_over_receipt(po_qty: float, receipt_qty: float,
                        tolerance_pct: float = 10.0) -> ConstraintVerdict:
    """BLOCK receipt that exceeds PO qty + tolerance."""
    max_receipt = po_qty * (1 + tolerance_pct / 100)
    if receipt_qty > max_receipt:
        excess = receipt_qty - max_receipt
        return ConstraintVerdict(
            result=CheckResult.BLOCK,
            code="PO_OVER_RECEIPT",
            message=f"收貨 {receipt_qty} 超過 PO 允許上限 {max_receipt:.0f}（{po_qty} + {tolerance_pct}%），超收 {excess:.0f}",
            alternatives=[
                f"按 PO 量 {po_qty} 收貨，超量退回供應商",
                f"申請超收核准（需採購主管簽核）",
            ],
            required_approval_role="purchasing",
        )
    return ConstraintVerdict(result=CheckResult.PASS, message="")


def check_po_approval(amount: float, role: str,
                       tier1_limit: float = 100000,
                       tier2_limit: float = 500000) -> ConstraintVerdict:
    """BLOCK (for self-service) or WARN based on PO amount & role."""
    if amount > tier2_limit:
        return ConstraintVerdict(
            result=CheckResult.BLOCK if role != "director" else CheckResult.PASS,
            code="PO_NEEDS_DIRECTOR",
            message=f"採購金額 NT${amount:,.0f} 超過 NT${tier2_limit:,.0f}，需廠長核准",
            required_approval_role="director",
        )
    if amount > tier1_limit:
        return ConstraintVerdict(
            result=CheckResult.WARN,
            code="PO_NEEDS_MANAGER",
            message=f"採購金額 NT${amount:,.0f} 超過 NT${tier1_limit:,.0f}，建議採購主管審閱",
            required_approval_role="purchasing" if role == "purchasing" else None,
        )
    return ConstraintVerdict(result=CheckResult.PASS, message="")


def check_supplier_score(score: float) -> ConstraintVerdict:
    """BLOCK if supplier score below 3.0."""
    if score < 2.0:
        return ConstraintVerdict(
            result=CheckResult.BLOCK,
            code="SUPPLIER_LOCKED",
            message=f"該供應商評分 {score} 低於 2.0，已自動鎖定，不可下單",
            alternatives=[f"聯繫供應商要求改善", f"選擇替代供應商"],
        )
    if score < 3.0:
        return ConstraintVerdict(
            result=CheckResult.WARN,
            code="SUPPLIER_LOW_SCORE",
            message=f"該供應商評分 {score} 低於 3.0，建議謹慎評估",
            alternatives=[f"要求供應商提出改善計劃", f"增加進料檢驗頻率"],
        )
    return ConstraintVerdict(result=CheckResult.PASS, message="")


def check_supplier_late_penalty(days_late: int) -> ConstraintVerdict:
    """INFO-level — auto-penalty on late delivery."""
    if days_late > 0:
        penalty_pts = min(days_late * 0.5, 15)  # max 15 points off
        return ConstraintVerdict(
            result=CheckResult.WARN,
            code="SUPPLIER_LATE",
            message=f"此供應商逾期 {days_late} 天，評分將扣 {penalty_pts:.1f} 分",
            details="連續逾期3次將自動鎖定供應商",
        )
    return ConstraintVerdict(result=CheckResult.PASS, message="")


# ═══════════════════════════════════════════════════════════════════
# BOM CONSTRAINTS
# ═══════════════════════════════════════════════════════════════════

def check_bom_circular(bom_tree: dict, parent_id: str,
                        new_child_id: str, visited: Optional[set] = None) -> ConstraintVerdict:
    """BLOCK if adding a component creates a circular reference (A→B→A)."""
    if visited is None:
        visited = set()
    if parent_id in visited:
        return ConstraintVerdict(
            result=CheckResult.BLOCK,
            code="BOM_CIRCULAR",
            message=f"循環引用：{new_child_id} 的 BOM 鏈中已包含 {parent_id}（A→B→A）",
            details="BOM 不可包含自己的上層組件",
        )
    visited.add(parent_id)
    children = bom_tree.get(new_child_id, [])
    for child in children:
        result = check_bom_circular(bom_tree, parent_id, child, visited)
        if result.result != CheckResult.PASS:
            return result
    visited.discard(parent_id)
    return ConstraintVerdict(result=CheckResult.PASS, message="")


def check_active_bom_edit(bom_status: str) -> ConstraintVerdict:
    """BLOCK editing BOM that's being used by open work orders."""
    if bom_status == "active":
        return ConstraintVerdict(
            result=CheckResult.WARN,
            code="BOM_ACTIVE_EDIT",
            message="此 BOM 正在使用中（有工單已引用），修改將影響現有工單",
            alternatives=[
                f"建立新版本 BOM（ECR/ECO 流程）",
                f"暫不修改，於下次排產時套用變更",
            ],
        )
    return ConstraintVerdict(result=CheckResult.PASS, message="")


# ═══════════════════════════════════════════════════════════════════
# PRODUCTION CONSTRAINTS
# ═══════════════════════════════════════════════════════════════════

def check_wo_release_readiness(materials_available: bool,
                                 routing_defined: bool) -> ConstraintVerdict:
    """BLOCK WO release if materials not available or routing missing."""
    issues = []
    if not materials_available:
        issues.append("物料不足（部分料件庫存不足或未到貨）")
    if not routing_defined:
        issues.append("製程途程未定義（缺少工序站點）")

    if issues:
        return ConstraintVerdict(
            result=CheckResult.BLOCK,
            code="WO_NOT_READY",
            message="工單不具備釋出條件",
            details="；".join(issues),
            alternatives=[
                f"待物料到齊後釋出（預計到料日 05/08）",
                f"部分釋出可先行工序（需生管核准）",
            ],
        )
    return ConstraintVerdict(result=CheckResult.PASS, message="")


def check_wo_close_reconciliation(planned_qty: float, produced_qty: float,
                                    scrapped_qty: float,
                                    issued_material_cost: float,
                                    bom_material_cost: float) -> ConstraintVerdict:
    """WARN if WO has material variances or yield issues."""
    issues = []
    yield_pct = (produced_qty / planned_qty * 100) if planned_qty > 0 else 0
    if yield_pct < 85:
        issues.append(f"良率 {yield_pct:.1f}%（目標 ≥85%），差異 {planned_qty - produced_qty} 件")
    cost_var = issued_material_cost - bom_material_cost
    if cost_var > 0:
        var_pct = (cost_var / bom_material_cost * 100) if bom_material_cost > 0 else 0
        issues.append(f"材料超耗 NT${cost_var:,.0f}（{var_pct:.1f}%）")

    if issues:
        return ConstraintVerdict(
            result=CheckResult.WARN,
            code="WO_CLOSE_VARIANCE",
            message="工單關閉前需確認以下差異",
            details="；".join(issues),
            alternatives=[
                f"接受差異並關閉（超出部分列為製造成本）",
                f"暫不關閉，待調查差異原因",
                f"調整 BOM 標準用量以符合實際（需工程核准）",
            ],
        )
    return ConstraintVerdict(result=CheckResult.PASS, message="")


def check_rush_order_cascade(wo_ref: str, existing_orders: list[dict]) -> ConstraintVerdict:
    """WARN about impact of rush order insertion on existing schedule."""
    affected = []
    for order in existing_orders:
        delay = order.get("estimated_delay_days", 0)
        if delay > 0:
            affected.append(f"{order['wo_ref']}（延遲 {delay} 天）")

    if affected:
        return ConstraintVerdict(
            result=CheckResult.WARN,
            code="WO_RUSH_CASCADE",
            message=f"急單 {wo_ref} 插隊將影響以下工單",
            details="、".join(affected),
            affected_entities=[a.split("（")[0] for a in affected],
            alternatives=[
                f"評估急單必要性，是否可延後 1 天",
                f"安排加班消化受影響工單",
                f"將部分工單外發加工",
            ],
        )
    return ConstraintVerdict(result=CheckResult.PASS, message="")


# ═══════════════════════════════════════════════════════════════════
# QUALITY CONSTRAINTS
# ═══════════════════════════════════════════════════════════════════

def check_qc_hold(item: str, lot: Optional[str],
                   inspection_status: str) -> ConstraintVerdict:
    """BLOCK if material is under QC hold."""
    if inspection_status == "pending":
        return ConstraintVerdict(
            result=CheckResult.BLOCK,
            code="QC_PENDING",
            message=f"{item} 批號 {lot} 待檢驗中，不可發料",
            details="需完成進料檢驗並做出使用決策 (Usage Decision)",
        )
    if inspection_status == "rejected":
        return ConstraintVerdict(
            result=CheckResult.BLOCK,
            code="QC_REJECTED",
            message=f"{item} 批號 {lot} 檢驗不合格，不可使用",
            alternatives=[
                f"退回供應商",
                f"申請特採（需品管 + 廠長核准）",
                f"申請報廢",
            ],
        )
    return ConstraintVerdict(result=CheckResult.PASS, message="")


def check_nc_cascade(nc_ref: str, affected_lots: list[str]) -> ConstraintVerdict:
    """BLOCK usage of lots affected by an open non-conformance."""
    if affected_lots:
        return ConstraintVerdict(
            result=CheckResult.BLOCK,
            code="NC_LOT_BLOCKED",
            message=f"NC {nc_ref} 未結案，受影響批號 {', '.join(affected_lots)} 已鎖定",
            alternatives=[
                f"完成 NC 處置後解鎖",
                f"對受影響批次逐批檢驗（合格者解鎖）",
            ],
        )
    return ConstraintVerdict(result=CheckResult.PASS, message="")


def check_recurring_defect(defect_code: str, count_3m: int) -> ConstraintVerdict:
    """WARN → MRB if same defect appears 3+ times in 3 months."""
    if count_3m >= 5:
        return ConstraintVerdict(
            result=CheckResult.WARN,
            code="QC_RECURRING_MRB",
            message=f"缺陷 {defect_code} 近3個月發生 {count_3m} 次，需召開 MRB",
            details="Material Review Board 需由品管、工程、生產三方會審",
            required_approval_role="director",
        )
    if count_3m >= 3:
        return ConstraintVerdict(
            result=CheckResult.WARN,
            code="QC_RECURRING_WARN",
            message=f"缺陷 {defect_code} 近3個月發生 {count_3m} 次，建議啟動 CAPA",
        )
    return ConstraintVerdict(result=CheckResult.PASS, message="")


# ═══════════════════════════════════════════════════════════════════
# FINANCE CONSTRAINTS
# ═══════════════════════════════════════════════════════════════════

def check_month_end_lock(period: str, current_date: datetime) -> ConstraintVerdict:
    """BLOCK posting to a closed accounting period."""
    # Simple check: if current date is past period's close date
    period_end = _parse_period_end(period)
    if period_end and current_date > period_end:
        return ConstraintVerdict(
            result=CheckResult.BLOCK,
            code="FI_MONTH_CLOSED",
            message=f"期間 {period} 已關帳，不可異動",
            details=f"關帳日 {period_end.date()}，如需修正請開啟調整期",
        )
    return ConstraintVerdict(result=CheckResult.PASS, message="")


def _parse_period_end(period: str) -> Optional[datetime]:
    """Parse '2026-05' to end of month."""
    try:
        parts = period.split("-")
        y, m = int(parts[0]), int(parts[1])
        if m == 12:
            return datetime(y + 1, 1, 1) - timedelta(days=1)
        return datetime(y, m + 1, 1) - timedelta(days=1)
    except (IndexError, ValueError):
        return None


def check_double_entry(event_type: str) -> ConstraintVerdict:
    """WARN if an inventory movement lacks corresponding accounting entry."""
    # This is a placeholder — actual check requires DB query
    required_pairs = {
        "material.received": "在途→庫存，同時產生應付（供應商負債）",
        "material.issued": "庫存→在製品（WIP），成本轉移",
        "scrap": "在製品→報廢損失，成本轉費用",
        "finished_goods_receipt": "在製品→成品，存貨形態轉換",
    }
    pair = required_pairs.get(event_type)
    if pair:
        return ConstraintVerdict(
            result=CheckResult.WARN,
            code="FI_DOUBLE_ENTRY",
            message=f"庫存異動「{event_type}」需對應會計分錄：{pair}",
            details="系統自動產生傳票，請確認科目正確",
        )
    return ConstraintVerdict(result=CheckResult.PASS, message="")


def check_ar_block_shipment(customer: str, overdue_days: int,
                              overdue_amount: float) -> ConstraintVerdict:
    """BLOCK shipment if customer has >30 days overdue."""
    if overdue_days > 60:
        return ConstraintVerdict(
            result=CheckResult.BLOCK,
            code="AR_BLOCK_SHIPMENT",
            message=f"客戶 {customer} 逾期 {overdue_days} 天（NT${overdue_amount:,.0f}），已鎖定出貨",
            alternatives=[
                f"聯繫客戶支付逾期款項後解鎖",
                f"申請特放出貨（需廠長核准）",
            ],
            required_approval_role="director",
        )
    if overdue_days > 30:
        return ConstraintVerdict(
            result=CheckResult.WARN,
            code="AR_OVERDUE_WARN",
            message=f"客戶 {customer} 逾期 {overdue_days} 天（NT${overdue_amount:,.0f}），建議暫停出貨",
            alternatives=[f"通知業務催收", f"申請特放出貨"],
        )
    return ConstraintVerdict(result=CheckResult.PASS, message="")


# ── Cash Flow Constraints ──────────────────────────────────────────


def check_cash_sufficient(cash_balance: float, po_amount: float,
                           projected_balance: float = 0) -> ConstraintVerdict:
    """BLOCK PO if cash insufficient (現金不足鎖定採購)."""
    min_reserve = cash_balance * 0.1
    available = cash_balance + projected_balance - min_reserve
    if po_amount > available + min_reserve:
        return ConstraintVerdict(
            result=CheckResult.BLOCK,
            code="CASH_INSUFFICIENT",
            message=f"現金不足（可用 NT${available:,.0f} < PO NT${po_amount:,.0f}），已鎖定採購單",
            alternatives=[
                f"採購金額降為 NT${available:,.0f}",
                f"延後付款協商供應商",
                f"申請緊急資金（需廠長核准）",
            ],
            required_approval_role="director",
        )
    if po_amount > available * 0.8:
        return ConstraintVerdict(
            result=CheckResult.WARN,
            code="CASH_TIGHT",
            message=f"現金吃緊，PO NT${po_amount:,.0f} 將使可用資金低於 NT${cash_balance - po_amount:,.0f}",
            alternatives=[f"分批下單", f"確認應收帳款入帳時間"],
        )
    return ConstraintVerdict(result=CheckResult.PASS, message="")


def check_rush_cash_impact(so_amount: float, premium_pct: float,
                             overtime_cost: float, delay_penalties: float,
                             cash_balance: float) -> ConstraintVerdict:
    """WARN/BLOCK rush order if financial impact is negative (急單財務風險)."""
    net = so_amount * (1 + premium_pct) - overtime_cost - delay_penalties
    if net < 0:
        return ConstraintVerdict(
            result=CheckResult.BLOCK,
            code="RUSH_NEGATIVE",
            message=f"急單淨效益為負（NT${net:,.0f}），溢價不足以覆蓋成本",
            alternatives=[
                f"提高溢價至 {(abs(net) / so_amount + 0.2) * 100:.0f}%",
                f"按正常排程生產",
                f"部分外包降低成本",
            ],
            required_approval_role="director",
        )
    if net < so_amount * 0.05:
        return ConstraintVerdict(
            result=CheckResult.WARN,
            code="RUSH_LOW_MARGIN",
            message=f"急單利潤偏低（NT${net:,.0f}，margin {net / (so_amount * (1 + premium_pct)) * 100:.1f}%）",
            alternatives=[f"協調客戶提高溢價", f"重新評估插單排程"],
        )
    return ConstraintVerdict(result=CheckResult.PASS, message="")


def check_contract_active(contract_status: str, end_date: Optional[datetime] = None,
                            days_to_expiry: int = 30) -> ConstraintVerdict:
    """WARN if contract expiring or inactive (合約即將到期)."""
    if contract_status in ("expired", "terminated"):
        return ConstraintVerdict(
            result=CheckResult.BLOCK,
            code="CONTRACT_INACTIVE",
            message=f"合約狀態為 {contract_status}，無法建立銷售訂單",
            alternatives=[f"續約合約", f"重新簽訂合約"],
        )
    if end_date and days_to_expiry <= 30:
        return ConstraintVerdict(
            result=CheckResult.WARN,
            code="CONTRACT_EXPIRING",
            message=f"合約將於 {days_to_expiry} 天後到期",
            alternatives=[f"啟動續約流程", f"聯繫客戶確認續約意願"],
        )
    return ConstraintVerdict(result=CheckResult.PASS, message="")


# ═══════════════════════════════════════════════════════════════════
# ORCHESTRATOR
# ═══════════════════════════════════════════════════════════════════

class ConstraintChecker:
    """Runs all applicable constraint checks for an operation."""

    def __init__(self):
        self._registry: dict[str, list[Callable[[dict, str], ConstraintVerdict]]] = {}

    def register(self, operation: str, check_fn: Callable):
        if operation not in self._registry:
            self._registry[operation] = []
        self._registry[operation].append(check_fn)

    def check(self, operation: str, params: dict,
              actor_role: str = "") -> list[ConstraintVerdict]:
        results: list[ConstraintVerdict] = []
        for check_fn in self._registry.get(operation, []):
            try:
                verdict = check_fn(params, actor_role)
                results.append(verdict)
            except Exception as e:
                logger.exception("Constraint check failed for %s", operation)
                results.append(ConstraintVerdict(
                    result=CheckResult.BLOCK,
                    code="CHECK_ERROR",
                    message=f"約束檢查異常: {e}",
                ))
        return results

    def has_blocks(self, verdicts: list[ConstraintVerdict]) -> bool:
        return any(v.result == CheckResult.BLOCK for v in verdicts)

    def has_warnings(self, verdicts: list[ConstraintVerdict]) -> bool:
        return any(v.result == CheckResult.WARN for v in verdicts)

    def summary(self, verdicts: list[ConstraintVerdict]) -> dict:
        return {
            "blocks": [v for v in verdicts if v.result == CheckResult.BLOCK],
            "warnings": [v for v in verdicts if v.result == CheckResult.WARN],
            "pass": [v for v in verdicts if v.result == CheckResult.PASS],
            "can_proceed": not self.has_blocks(verdicts),
        }


# ─── Global Instance ──────────────────────────────────────────────

_checker: ConstraintChecker | None = None


def get_checker() -> ConstraintChecker:
    global _checker
    if _checker is None:
        _checker = ConstraintChecker()
        _register_all(_checker)
    return _checker


def reset_checker():
    """For testing — re-register all defaults."""
    global _checker
    _checker = ConstraintChecker()
    _register_all(_checker)


# ─── Registration ─────────────────────────────────────────────────

def _register_all(checker: ConstraintChecker):
    """Register all business rule checks."""

    # ── Inventory ──
    def _inv_outbound(p, role):
        return check_negative_stock(
            p.get("item", ""), p.get("on_hand", 0), p.get("quantity", 0))

    def _inv_safety(p, role):
        return check_safety_stock(
            p.get("item", ""), p.get("on_hand", 0), p.get("quantity", 0),
            p.get("safety_stock", 0))

    def _inv_expiry(p, role):
        return check_expiry(
            p.get("item", ""), p.get("lot"), p.get("expiry_date"))

    def _inv_dormant(p, role):
        return check_dormant_stock(
            p.get("item", ""), p.get("last_movement_days", 0), p.get("on_hand", 0))

    def _inv_count(p, role):
        return check_cycle_count_variance(
            p.get("item", ""), p.get("recorded_qty", 0), p.get("actual_qty", 0))

    # ── Purchase ──
    def _pur_receipt(p, role):
        return check_over_receipt(p.get("po_qty", 0), p.get("receipt_qty", 0))

    def _pur_approval(p, role):
        return check_po_approval(p.get("amount", 0), role)

    def _pur_supplier(p, role):
        return check_supplier_score(p.get("supplier_score", 5.0))

    def _pur_late(p, role):
        return check_supplier_late_penalty(p.get("days_late", 0))

    # ── BOM ──
    def _bom_circular(p, role):
        return check_bom_circular(
            p.get("bom_tree", {}), p.get("parent_id", ""), p.get("child_id", ""))

    def _bom_active(p, role):
        return check_active_bom_edit(p.get("bom_status", "draft"))

    # ── Production ──
    def _wo_release(p, role):
        return check_wo_release_readiness(
            p.get("materials_available", True), p.get("routing_defined", True))

    def _wo_close(p, role):
        return check_wo_close_reconciliation(
            p.get("planned_qty", 0), p.get("produced_qty", 0),
            p.get("scrapped_qty", 0), p.get("material_cost", 0),
            p.get("bom_cost", 0))

    def _wo_rush(p, role):
        return check_rush_order_cascade(
            p.get("wo_ref", ""), p.get("existing_orders", []))

    # ── Quality ──
    def _qc_hold(p, role):
        return check_qc_hold(
            p.get("item", ""), p.get("lot"), p.get("inspection_status", "approved"))

    def _nc_lock(p, role):
        return check_nc_cascade(
            p.get("nc_ref", ""), p.get("affected_lots", []))

    def _qc_recur(p, role):
        return check_recurring_defect(
            p.get("defect_code", ""), p.get("count_3m", 0))

    # ── Finance ──
    def _fi_close(p, role):
        return check_month_end_lock(
            p.get("period", ""), datetime.utcnow())

    def _fi_entry(p, role):
        return check_double_entry(p.get("event_type", ""))

    def _fi_ar(p, role):
        return check_ar_block_shipment(
            p.get("customer", ""), p.get("overdue_days", 0), p.get("overdue_amount", 0))

    # ── Cash Flow ──
    def _fi_cash(p, role):
        return check_cash_sufficient(
            p.get("cash_balance", 0), p.get("po_amount", 0), p.get("projected_balance", 0))

    def _fi_rush(p, role):
        return check_rush_cash_impact(
            p.get("so_amount", 0), p.get("premium_pct", 0.2),
            p.get("overtime_cost", 0), p.get("delay_penalties", 0),
            p.get("cash_balance", 0))

    def _fi_contract(p, role):
        return check_contract_active(
            p.get("contract_status", "active"), p.get("end_date"),
            p.get("days_to_expiry", 30))

    # Register all
    for ops in [
        ("issue_material", [_inv_outbound, _inv_safety, _inv_expiry]),
        ("transfer_stock", [_inv_outbound]),
        ("cycle_count", [_inv_count]),
        ("create_po", [_pur_approval, _pur_supplier]),
        ("receive_po", [_pur_receipt]),
        ("evaluate_supplier", [_pur_late]),
        ("edit_bom", [_bom_circular, _bom_active]),
        ("release_wo", [_wo_release]),
        ("close_wo", [_wo_close]),
        ("rush_order", [_wo_rush]),
        ("issue_qc_hold", [_qc_hold]),
        ("create_nc", [_nc_lock, _qc_recur]),
        ("close_period", [_fi_close]),
        ("ship_order", [_fi_ar]),
        ("inventory_movement", [_fi_entry]),
        ("create_po", [_fi_cash]),
        ("evaluate_rush_order", [_fi_rush]),
        ("create_so_with_contract", [_fi_contract]),
    ]:
        for fn in ops[1]:
            checker.register(ops[0], fn)
