#!/usr/bin/env python3
"""
LLM-ERP Data Management CLI

Standardized import/export tool for the LLM-ERP system.
All data uses natural keys (part_no, product_no, supplier name, etc.),
NOT internal UUIDs — so humans can read, edit, and share the files.

Usage:
    # Import sample data
    python -m scripts.manage_data import scripts/sample_data/

    # Import a single CSV file
    python -m scripts.manage_data import scripts/sample_data/01-parts.csv

    # Dry-run (validate only, no changes)
    python -m scripts.manage_data import scripts/sample_data/ --dry-run

    # Export current database to CSV files
    python -m scripts.manage_data export ./exported_data/

    # Reset all data (clears every table)
    python -m scripts.manage_data reset

    # List all importable entities and their schemas
    python -m scripts.manage_data schema

  NOTE: API keys are NEVER included in imported/exported data.
        They live ONLY in backend/.env.

Data file naming convention (for directory imports):
    01-*.csv — parts, suppliers, products, work-centers, accounts (no FK)
    06-*.csv — inventory (FK→parts)
    07-*.csv — bom (FK→products, parts)
    08-*.csv — purchase-orders (FK→suppliers, parts)
    09-*.csv — production-orders (FK→products)
    10-*.csv — quality (FK→parts, purchase-orders)
    11-*.csv — accounting (FK→accounts)
    12-*.csv — ar (accounts receivable, no FK)
    20-*.csv — dispatch-logs (FK→production-orders, work-centers)
"""

import asyncio
import csv
import json
import os
import sys
import logging
import uuid
from datetime import date, datetime
from pathlib import Path
from typing import Any

# Suppress SQLAlchemy INFO logging so output is clean
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

# ── Add parent to path so we can import the app ─────────────
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select, text
from app.database import async_session, init_db
from app.models.inventory import Part, Inventory, InventoryTransaction
from app.models.purchase import Supplier, PurchaseOrder, PurchaseOrderItem
from app.models.bom import Product, BOMItem
from app.models.dispatch import (
    WorkCenter, ProductionOrder, Operation, DispatchLog,
    OrderStatus, OpStatus, WCStatus,
)
from app.models.quality import (
    InspectionOrder, InspectionResult, NonConformance, CAPARecord,
)
from app.models.accounting import (
    Account, JournalEntry, JournalLine, AccountsReceivable, MonthEndClose,
)

# ─── Entity Registry ───────────────────────────────────────────

IMPORT_ORDER = [
    # (entity_name, csv_filename_glob, import_fn, [dependencies])
    ("parts", "01-*", "import_parts", []),
    ("suppliers", "02-*", "import_suppliers", []),
    ("products", "03-*", "import_products", []),
    ("work-centers", "04-*", "import_work_centers", []),
    ("accounts", "05-*", "import_accounts", []),
    ("inventory", "06-*", "import_inventory", ["parts"]),
    ("bom", "07-*", "import_bom", ["products", "parts"]),
    ("purchase-orders", "08-*", "import_purchase_orders", ["suppliers", "parts"]),
    ("production-orders", "09-*", "import_production_orders", ["products", "work-centers"]),
    ("quality", "10-*", "import_quality", ["parts", "purchase-orders"]),
    ("accounting", "11-*", "import_accounting", ["accounts"]),
    ("ar", "12-*", "import_ar", []),
    ("dispatch-logs", "20-*", "import_dispatch_logs", ["production-orders", "work-centers"]),
]


def _parse_bool(v: str) -> bool:
    return v.strip().lower() in ("true", "1", "yes", "y")


def _parse_date(v: str) -> date | None:
    if not v or v.strip() == "":
        return None
    return date.fromisoformat(v.strip()[:10])


def _parse_datetime(v: str) -> datetime | None:
    if not v or v.strip() == "":
        return None
    return datetime.fromisoformat(v.strip())


def _parse_float(v: str) -> float:
    if not v or v.strip() == "":
        return 0.0
    return float(v.strip())


def _parse_int(v: str) -> int:
    if not v or v.strip() == "":
        return 0
    return int(v.strip())


# ─── Resolver caches ──────────────────────────────────────────

part_cache: dict[str, str] = {}       # part_no → UUID
supplier_cache: dict[str, str] = {}   # name → UUID
product_cache: dict[str, str] = {}    # product_no → UUID
wc_cache: dict[str, str] = {}         # name → ID (string)
account_cache: dict[str, str] = {}    # account_no → UUID
po_cache: dict[str, str] = {}         # po_no → UUID
prod_order_cache: dict[str, str] = {} # order_no → ID


async def _build_caches(db):
    """Pre-load all FK resolution maps so imports are fast."""
    global part_cache, supplier_cache, product_cache, wc_cache
    global account_cache, po_cache, prod_order_cache

    result = await db.execute(select(Part.part_no, Part.id))
    part_cache = {r[0]: str(r[1]) for r in result}

    result = await db.execute(select(Supplier.name, Supplier.id))
    supplier_cache = {r[0]: str(r[1]) for r in result}

    result = await db.execute(select(Product.product_no, Product.id))
    product_cache = {r[0]: str(r[1]) for r in result}

    result = await db.execute(select(WorkCenter.name, WorkCenter.id))
    wc_cache = {r[0]: str(r[1]) for r in result}

    result = await db.execute(select(Account.account_no, Account.id))
    account_cache = {r[0]: str(r[1]) for r in result}

    result = await db.execute(select(PurchaseOrder.po_no, PurchaseOrder.id))
    po_cache = {r[0]: str(r[1]) for r in result}

    result = await db.execute(select(ProductionOrder.order_no, ProductionOrder.id))
    prod_order_cache = {r[0]: str(r[1]) for r in result}


def _resolve_part(part_no: str) -> uuid.UUID:
    pid = part_cache.get(part_no)
    if not pid:
        raise ValueError(f"Part not found: {part_no}")
    return uuid.UUID(pid)


def _resolve_supplier(name: str) -> uuid.UUID:
    sid = supplier_cache.get(name)
    if not sid:
        raise ValueError(f"Supplier not found: {name}")
    return uuid.UUID(sid)


def _resolve_product(product_no: str) -> uuid.UUID:
    pid = product_cache.get(product_no)
    if not pid:
        raise ValueError(f"Product not found: {product_no}")
    return uuid.UUID(pid)


def _resolve_wc(name: str) -> str:
    wid = wc_cache.get(name)
    if not wid:
        raise ValueError(f"Work center not found: {name}")
    return wid


def _resolve_account(account_no: str) -> uuid.UUID:
    aid = account_cache.get(account_no)
    if not aid:
        raise ValueError(f"Account not found: {account_no}")
    return uuid.UUID(aid)


def _resolve_po(po_no: str) -> uuid.UUID:
    pid = po_cache.get(po_no)
    if not pid:
        raise ValueError(f"Purchase order not found: {po_no}")
    return uuid.UUID(pid)


def _resolve_prod_order(order_no: str) -> str:
    oid = prod_order_cache.get(order_no)
    if not oid:
        raise ValueError(f"Production order not found: {order_no}")
    return oid


# ─── Import Functions ─────────────────────────────────────────

async def import_parts(db, rows: list[dict]) -> tuple[int, int]:
    """rows: [{"part_no","name","spec","unit","category"}, ...]"""
    imported = 0
    skipped = 0
    for row in rows:
        pno = row["part_no"].strip()
        if pno in part_cache:
            skipped += 1
            continue
        p = Part(
            part_no=pno,
            name=row.get("name", "").strip(),
            spec=row.get("spec", "").strip() or None,
            unit=row.get("unit", "pcs").strip(),
            category=row.get("category", "").strip() or None,
        )
        db.add(p)
        await db.flush()
        part_cache[pno] = str(p.id)
        imported += 1
    return imported, skipped


async def import_suppliers(db, rows: list[dict]) -> tuple[int, int]:
    imported = 0
    skipped = 0
    for row in rows:
        name = row["name"].strip()
        if name in supplier_cache:
            skipped += 1
            continue
        s = Supplier(
            name=name,
            contact=row.get("contact", "").strip() or None,
            phone=row.get("phone", "").strip() or None,
            email=row.get("email", "").strip() or None,
            score=_parse_float(row.get("score", "5.0")),
        )
        db.add(s)
        await db.flush()
        supplier_cache[name] = str(s.id)
        imported += 1
    return imported, skipped


async def import_products(db, rows: list[dict]) -> tuple[int, int]:
    imported = 0
    skipped = 0
    for row in rows:
        pno = row["product_no"].strip()
        if pno in product_cache:
            skipped += 1
            continue
        p = Product(
            product_no=pno,
            name=row.get("name", "").strip(),
            description=row.get("description", "").strip() or None,
        )
        db.add(p)
        await db.flush()
        product_cache[pno] = str(p.id)
        imported += 1
    return imported, skipped


async def import_work_centers(db, rows: list[dict]) -> tuple[int, int]:
    """Rows use UUID-style primary keys; skip if name exists."""
    imported = 0
    skipped = 0
    for row in rows:
        name = row["name"].strip()
        if name in wc_cache:
            skipped += 1
            continue
        wc = WorkCenter(
            name=name,
            description=row.get("description", "").strip(),
            status=row.get("status", "idle").strip(),
            capacity_hours=_parse_float(row.get("capacity_hours", "8.0")),
            efficiency=_parse_float(row.get("efficiency", "1.0")),
            location=row.get("location", "").strip(),
            alternate_group=row.get("alternate_group", "").strip(),
        )
        db.add(wc)
        await db.flush()
        wc_cache[name] = str(wc.id)
        imported += 1
    return imported, skipped


async def import_accounts(db, rows: list[dict]) -> tuple[int, int]:
    imported = 0
    skipped = 0
    for row in rows:
        ano = row["account_no"].strip()
        if ano in account_cache:
            skipped += 1
            continue
        acc = Account(
            account_no=ano,
            name=row.get("name", "").strip(),
            type=row.get("type", "asset").strip(),
            normal_balance=row.get("normal_balance", "debit").strip(),
            is_active=_parse_bool(row.get("is_active", "true")),
        )
        db.add(acc)
        await db.flush()
        account_cache[ano] = str(acc.id)
        imported += 1
    return imported, skipped


async def import_inventory(db, rows: list[dict]) -> tuple[int, int]:
    imported = 0
    skipped = 0
    for row in rows:
        part_no = row["part_no"].strip()
        pid = _resolve_part(part_no)
        loc = row.get("location", "").strip() or None
        qty = _parse_float(row.get("quantity", "0"))
        inv = Inventory(part_id=pid, location=loc, quantity=qty)
        db.add(inv)
        imported += 1
    await db.flush()
    return imported, skipped


async def import_bom(db, rows: list[dict]) -> tuple[int, int]:
    imported = 0
    skipped = 0
    for row in rows:
        product_no = row["product_no"].strip()
        part_no = row["part_no"].strip()
        pid = _resolve_product(product_no)
        ptid = _resolve_part(part_no)
        b = BOMItem(
            product_id=pid,
            part_id=ptid,
            quantity=_parse_float(row.get("quantity", "1")),
            level=_parse_int(row.get("level", "0")),
            sequence_no=_parse_int(row.get("sequence_no", "0")) or None,
        )
        db.add(b)
        imported += 1
    await db.flush()
    return imported, skipped


async def import_purchase_orders(db, rows: list[dict]) -> tuple[int, int]:
    """Rows may have multiple rows with same po_no (one per PO item).
    We group by po_no to create one PO with multiple items."""
    imported = 0
    skipped = 0
    grouped: dict[str, list[dict]] = {}
    for row in rows:
        pono = row["po_no"].strip()
        if pono not in grouped:
            grouped[pono] = []
        grouped[pono].append(row)

    for pono, item_rows in grouped.items():
        if pono in po_cache:
            skipped += len(item_rows)
            continue
        r0 = item_rows[0]
        sid = _resolve_supplier(r0["supplier_name"].strip())
        po = PurchaseOrder(
            po_no=pono,
            supplier_id=sid,
            status=r0.get("status", "draft").strip(),
            ordered_by=r0.get("ordered_by", "").strip() or None,
            notes=r0.get("notes", "").strip() or None,
        )
        db.add(po)
        await db.flush()
        po_cache[pono] = str(po.id)

        for row in item_rows:
            pid = _resolve_part(row["item_part_no"].strip())
            item = PurchaseOrderItem(
                po_id=po.id,
                part_id=pid,
                quantity=_parse_float(row.get("item_quantity", "1")),
                unit_price=_parse_float(row.get("item_unit_price", "0")) or None,
                expected_delivery=_parse_date(row.get("item_expected_delivery")),
                received_qty=_parse_float(row.get("item_received_qty", "0")),
            )
            db.add(item)
        imported += 1  # count POs, not items
    await db.flush()
    return imported, skipped


async def import_production_orders(db, rows: list[dict]) -> tuple[int, int]:
    """Each row = one production order (no multi-row grouping needed here)."""
    imported = 0
    skipped = 0
    for row in rows:
        ono = row["order_no"].strip()
        if ono in prod_order_cache:
            skipped += 1
            continue
        po = ProductionOrder(
            order_no=ono,
            product_no=row.get("product_no", "").strip(),
            product_name=row.get("product_name", "").strip(),
            quantity=_parse_float(row.get("quantity", "1")),
            due_date=_parse_date(row.get("due_date")),
            priority=_parse_int(row.get("priority", "3")),
            status=row.get("status", OrderStatus.DRAFT.value).strip(),
            notes=row.get("notes", "").strip() or "",
            created_by=row.get("created_by", "").strip() or "",
        )
        db.add(po)
        await db.flush()
        prod_order_cache[ono] = str(po.id)
        imported += 1

        # If operations are included in the same row, create them
        op_name = row.get("op_name", "").strip()
        if op_name:
            wc_name = row.get("op_work_center", "").strip()
            if wc_name:
                op = Operation(
                    order_id=po.id,
                    work_center_id=_resolve_wc(wc_name),
                    sequence_no=_parse_int(row.get("op_sequence", "1")),
                    name=op_name,
                    setup_time_min=_parse_float(row.get("op_setup", "0")),
                    cycle_time_min=_parse_float(row.get("op_cycle", "0")),
                    total_time_min=_parse_float(row.get("op_total", "0")),
                    status=row.get("op_status", OpStatus.PENDING.value).strip(),
                )
                db.add(op)
    await db.flush()
    return imported, skipped


async def import_quality(db, rows: list[dict]) -> tuple[int, int]:
    """Inspection orders. Multiple rows with same inspection_no = one IO + results."""
    imported = 0
    skipped = 0
    grouped: dict[str, list[dict]] = {}
    for row in rows:
        ino = row["inspection_no"].strip()
        if ino not in grouped:
            grouped[ino] = []
        grouped[ino].append(row)

    # Check existing
    result = await db.execute(
        select(InspectionOrder.inspection_no)
    )
    existing = {r[0] for r in result}

    for ino, item_rows in grouped.items():
        if ino in existing:
            skipped += len(item_rows)
            continue
        r0 = item_rows[0]
        insp = InspectionOrder(
            inspection_no=ino,
            part_id=_resolve_part(r0["part_no"].strip()),
            po_id=uuid.UUID(po_cache[r0["po_no"].strip()]) if r0.get("po_no", "").strip() and r0["po_no"].strip() in po_cache else None,
            lot_no=r0.get("lot_no", "").strip() or None,
            quantity=_parse_float(r0.get("quantity", "0")),
            status=r0.get("status", "pending").strip(),
            inspection_date=_parse_datetime(r0.get("inspection_date")),
            inspected_by=r0.get("inspected_by", "").strip() or None,
        )
        db.add(insp)
        await db.flush()

        for row in item_rows:
            item_no = row.get("item_no", "").strip()
            if not item_no:
                continue
            ir = InspectionResult(
                inspection_id=insp.id,
                item_no=item_no,
                description=row.get("item_description", "").strip() or None,
                spec_value=row.get("item_spec_value", "").strip() or None,
                measured_value=row.get("item_measured_value", "").strip() or None,
                result=row.get("item_result", "pass").strip(),
                notes=row.get("item_notes", "").strip() or None,
            )
            db.add(ir)

        imported += 1
    await db.flush()
    return imported, skipped


async def import_accounting(db, rows: list[dict]) -> tuple[int, int]:
    """Multi-row grouping by entry_no for journal entries + lines."""
    imported = 0
    skipped = 0
    grouped: dict[str, list[dict]] = {}
    for row in rows:
        eno = row["entry_no"].strip()
        if eno not in grouped:
            grouped[eno] = []
        grouped[eno].append(row)

    result = await db.execute(select(JournalEntry.entry_no))
    existing = {r[0] for r in result}

    for eno, item_rows in grouped.items():
        if eno in existing:
            skipped += len(item_rows)
            continue
        r0 = item_rows[0]
        entry = JournalEntry(
            entry_no=eno,
            description=r0.get("description", "").strip(),
            entry_date=_parse_date(r0.get("entry_date")),
            period=r0.get("period", "").strip(),
            source_type=r0.get("source_type", "").strip() or None,
            source_id=r0.get("source_id", "").strip() or None,
            created_by=r0.get("created_by", "import").strip(),
            posted=_parse_bool(r0.get("posted", "false")),
        )
        db.add(entry)
        await db.flush()

        for row in item_rows:
            line = JournalLine(
                entry_id=entry.id,
                account_id=_resolve_account(row["line_account_no"].strip()),
                debit=_parse_float(row.get("line_debit", "0")),
                credit=_parse_float(row.get("line_credit", "0")),
                description=row.get("line_description", "").strip() or None,
            )
            db.add(line)
        imported += 1
    await db.flush()
    return imported, skipped


async def import_ar(db, rows: list[dict]) -> tuple[int, int]:
    imported = 0
    skipped = 0
    for row in rows:
        ar = AccountsReceivable(
            customer_name=row.get("customer_name", "").strip(),
            invoice_no=row.get("invoice_no", "").strip(),
            amount=_parse_float(row.get("amount", "0")),
            due_date=_parse_date(row.get("due_date")),
            paid_amount=_parse_float(row.get("paid_amount", "0")),
            status=row.get("status", "open").strip(),
        )
        db.add(ar)
        imported += 1
    await db.flush()
    return imported, skipped


async def import_dispatch_logs(db, rows: list[dict]) -> tuple[int, int]:
    imported = 0
    skipped = 0
    for row in rows:
        dl = DispatchLog(
            order_id=_resolve_prod_order(row["order_no"].strip()) if row.get("order_no") else None,
            operation_id=None,  # would need operation lookup
            work_center_id=_resolve_wc(row["work_center_name"].strip()) if row.get("work_center_name") else None,
            action=row.get("action", "dispatch").strip(),
        )
        db.add(dl)
        imported += 1
    await db.flush()
    return imported, skipped


# ─── Import Router ────────────────────────────────────────────

IMPORT_FUNCS = {
    "parts": import_parts,
    "suppliers": import_suppliers,
    "products": import_products,
    "work-centers": import_work_centers,
    "accounts": import_accounts,
    "inventory": import_inventory,
    "bom": import_bom,
    "purchase-orders": import_purchase_orders,
    "production-orders": import_production_orders,
    "quality": import_quality,
    "accounting": import_accounting,
    "ar": import_ar,
    "dispatch-logs": import_dispatch_logs,
}


# ─── CSV Utility ──────────────────────────────────────────────

def read_csv(path: str) -> list[dict[str, str]]:
    with open(path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        return [row for row in reader]


def write_csv(path: str, fieldnames: list[str], rows: list[dict]):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


# ─── Main Commands ────────────────────────────────────────────

async def cmd_import(source: str, dry_run: bool = False):
    """Import from a CSV file or directory of CSV files."""
    await init_db()
    async with async_session() as db:
        await _build_caches(db)

        # Collect CSV files
        csv_files = []
        if os.path.isdir(source):
            for ent_name, glob_pat, import_fn_name, deps in IMPORT_ORDER:
                # Find matching files
                for f in sorted(os.listdir(source)):
                    if not f.endswith(".csv"):
                        continue
                    # Match glob pattern — simple prefix match
                    prefix = glob_pat.replace("-*", "-")
                    if f.startswith(prefix):
                        csv_files.append((ent_name, os.path.join(source, f)))
                        break
                # Also catch any file matching the prefix
            if not csv_files:
                # Fallback: load everything sorted
                for f in sorted(os.listdir(source)):
                    if f.endswith(".csv"):
                        csv_files.append((f, os.path.join(source, f)))
        elif os.path.isfile(source):
            # Infer entity from filename
            fname = os.path.basename(source)
            matched = False
            for ent_name, glob_pat, import_fn_name, deps in IMPORT_ORDER:
                prefix = glob_pat.replace("-*", "-")
                if fname.startswith(prefix):
                    csv_files.append((ent_name, source))
                    matched = True
                    break
            if not matched:
                print(f"⚠️  Could not infer entity type from {fname}. Using filename as-is.")
                csv_files.append((fname.replace(".csv", ""), source))
        else:
            print(f"❌ Source not found: {source}")
            sys.exit(1)

        total_imported = 0
        total_skipped = 0
        for ent_name, csv_path in csv_files:
            print(f"\n📄 {os.path.basename(csv_path)} → {ent_name}")
            rows = read_csv(csv_path)
            if not rows:
                print("   (empty - skipped)")
                continue
            print(f"   {len(rows)} rows")

            if dry_run:
                print(f"   ✅ [DRY RUN] would import {len(rows)} rows")
                total_imported += len(rows)
                continue

            func = IMPORT_FUNCS.get(ent_name)
            if not func:
                print(f"   ⚠️  No import handler for '{ent_name}', skipping")
                continue

            try:
                imported, skipped = await func(db, rows)
                print(f"   ✅ {imported} imported, {skipped} skipped")
                total_imported += imported
                total_skipped += skipped
            except ValueError as e:
                print(f"   ❌ {e}")
                if not dry_run:
                    await db.rollback()
                sys.exit(1)

        await db.commit()
        print(f"\n{'='*50}")
        print(f"📊 Total: {total_imported} imported, {total_skipped} skipped")
        if dry_run:
            print("(dry run — no changes made)")
        print(f"{'='*50}")


async def cmd_export(output_dir: str):
    """Export all database tables to CSV files."""
    await init_db()
    async with async_session() as db:
        # ── Parts ──
        result = await db.execute(select(Part).order_by(Part.part_no))
        parts = result.scalars().all()
        write_csv(
            os.path.join(output_dir, "01-parts.csv"),
            ["part_no", "name", "spec", "unit", "category"],
            [{"part_no": p.part_no, "name": p.name, "spec": p.spec or "",
              "unit": p.unit, "category": p.category or ""}
             for p in parts],
        )
        print(f"📤 01-parts.csv: {len(parts)} parts")

        # ── Suppliers ──
        result = await db.execute(select(Supplier).order_by(Supplier.name))
        suppliers = result.scalars().all()
        write_csv(
            os.path.join(output_dir, "02-suppliers.csv"),
            ["name", "contact", "phone", "email", "score"],
            [{"name": s.name, "contact": s.contact or "", "phone": s.phone or "",
              "email": s.email or "", "score": s.score}
             for s in suppliers],
        )
        print(f"📤 02-suppliers.csv: {len(suppliers)} suppliers")

        # ── Products ──
        result = await db.execute(select(Product).order_by(Product.product_no))
        products = result.scalars().all()
        write_csv(
            os.path.join(output_dir, "03-products.csv"),
            ["product_no", "name", "description"],
            [{"product_no": p.product_no, "name": p.name, "description": p.description or ""}
             for p in products],
        )
        print(f"📤 03-products.csv: {len(products)} products")

        # ── Work Centers ──
        result = await db.execute(select(WorkCenter).order_by(WorkCenter.name))
        wcs = result.scalars().all()
        write_csv(
            os.path.join(output_dir, "04-work-centers.csv"),
            ["name", "description", "status", "capacity_hours", "efficiency", "location", "alternate_group"],
            [{"name": w.name, "description": w.description or "", "status": w.status,
              "capacity_hours": w.capacity_hours, "efficiency": w.efficiency,
              "location": w.location or "", "alternate_group": w.alternate_group or ""}
             for w in wcs],
        )
        print(f"📤 04-work-centers.csv: {len(wcs)} work centers")

        # ── Accounts ──
        result = await db.execute(select(Account).order_by(Account.account_no))
        accounts = result.scalars().all()
        write_csv(
            os.path.join(output_dir, "05-accounts.csv"),
            ["account_no", "name", "type", "normal_balance", "is_active"],
            [{"account_no": a.account_no, "name": a.name, "type": a.type,
              "normal_balance": a.normal_balance, "is_active": str(a.is_active).lower()}
             for a in accounts],
        )
        print(f"📤 05-accounts.csv: {len(accounts)} accounts")

        # ── Inventory ──
        result = await db.execute(
            select(Inventory, Part.part_no)
            .join(Part, Inventory.part_id == Part.id)
        )
        stock_rows = result.all()
        write_csv(
            os.path.join(output_dir, "06-inventory.csv"),
            ["part_no", "location", "quantity"],
            [{"part_no": r.part_no, "location": r.Inventory.location or "",
              "quantity": r.Inventory.quantity}
             for r in stock_rows],
        )
        print(f"📤 06-inventory.csv: {len(stock_rows)} stock records")

        # ── BOM ──
        result = await db.execute(
            select(BOMItem, Product.product_no, Part.part_no)
            .join(Product, BOMItem.product_id == Product.id)
            .join(Part, BOMItem.part_id == Part.id)
        )
        bom_rows = result.all()
        write_csv(
            os.path.join(output_dir, "07-bom.csv"),
            ["product_no", "part_no", "quantity", "level", "sequence_no"],
            [{"product_no": r.product_no, "part_no": r.part_no,
              "quantity": r.BOMItem.quantity, "level": r.BOMItem.level,
              "sequence_no": r.BOMItem.sequence_no or ""}
             for r in bom_rows],
        )
        print(f"📤 07-bom.csv: {len(bom_rows)} BOM items")

        # ── Purchase Orders ──
        result = await db.execute(
            select(
                PurchaseOrderItem,
                PurchaseOrder.po_no,
                PurchaseOrder.status.label("po_status"),
                PurchaseOrder.ordered_by,
                PurchaseOrder.notes.label("po_notes"),
                Supplier.name.label("supplier_name"),
                Part.part_no.label("item_part_no"),
            )
            .join(PurchaseOrder, PurchaseOrderItem.po_id == PurchaseOrder.id)
            .join(Supplier, PurchaseOrder.supplier_id == Supplier.id)
            .join(Part, PurchaseOrderItem.part_id == Part.id)
            .order_by(PurchaseOrder.po_no)
        )
        po_rows = result.all()
        write_csv(
            os.path.join(output_dir, "08-purchase-orders.csv"),
            ["po_no", "supplier_name", "status", "ordered_by", "notes",
             "item_part_no", "item_quantity", "item_unit_price", "item_expected_delivery", "item_received_qty"],
            [{"po_no": r.po_no, "supplier_name": r.supplier_name,
              "status": r.po_status or "",
              "ordered_by": r.ordered_by or "",
              "notes": r.po_notes or "",
              "item_part_no": r.item_part_no,
              "item_quantity": r.PurchaseOrderItem.quantity,
              "item_unit_price": r.PurchaseOrderItem.unit_price or "",
              "item_expected_delivery": r.PurchaseOrderItem.expected_delivery.isoformat() if r.PurchaseOrderItem.expected_delivery else "",
              "item_received_qty": r.PurchaseOrderItem.received_qty}
             for r in po_rows],
        )
        print(f"📤 08-purchase-orders.csv: {len(po_rows)} PO items")

        # ── Production Orders ──
        result = await db.execute(select(ProductionOrder).order_by(ProductionOrder.order_no))
        orders = result.scalars().all()
        write_csv(
            os.path.join(output_dir, "09-production-orders.csv"),
            ["order_no", "product_no", "product_name", "quantity", "due_date",
             "priority", "status", "notes", "created_by"],
            [{"order_no": o.order_no, "product_no": o.product_no,
              "product_name": o.product_name or "", "quantity": o.quantity,
              "due_date": o.due_date.isoformat() if o.due_date else "",
              "priority": o.priority, "status": o.status,
              "notes": o.notes or "", "created_by": o.created_by or ""}
             for o in orders],
        )
        print(f"📤 09-production-orders.csv: {len(orders)} orders")

        # ── Quality ──
        result = await db.execute(
            select(InspectionOrder, Part.part_no)
            .join(Part, InspectionOrder.part_id == Part.id)
        )
        inspections = result.all()
        write_csv(
            os.path.join(output_dir, "10-quality.csv"),
            ["inspection_no", "part_no", "po_no", "lot_no", "quantity",
             "status", "inspection_date", "inspected_by",
             "item_no", "item_description", "item_spec_value", "item_measured_value",
             "item_result", "item_notes"],
            [{"inspection_no": r.InspectionOrder.inspection_no,
              "part_no": r.part_no,
              "po_no": "",  # would need PO join
              "lot_no": r.InspectionOrder.lot_no or "",
              "quantity": r.InspectionOrder.quantity,
              "status": r.InspectionOrder.status,
              "inspection_date": r.InspectionOrder.inspection_date.isoformat() if r.InspectionOrder.inspection_date else "",
              "inspected_by": r.InspectionOrder.inspected_by or "",
              "item_no": "", "item_description": "", "item_spec_value": "",
              "item_measured_value": "", "item_result": "", "item_notes": ""}
             for r in inspections],
        )
        print(f"📤 10-quality.csv: {len(inspections)} inspections")

        # ── Accounting (Journal Entries) ──
        result = await db.execute(
            select(
                JournalLine,
                JournalEntry.entry_no,
                JournalEntry.description.label("entry_desc"),
                JournalEntry.entry_date,
                JournalEntry.period,
                JournalEntry.source_type,
                JournalEntry.source_id,
                JournalEntry.created_by,
                JournalEntry.posted,
                Account.account_no,
            )
            .join(JournalEntry, JournalLine.entry_id == JournalEntry.id)
            .join(Account, JournalLine.account_id == Account.id)
            .order_by(JournalEntry.entry_no)
        )
        jl_rows = result.all()
        write_csv(
            os.path.join(output_dir, "11-accounting.csv"),
            ["entry_no", "description", "entry_date", "period", "source_type", "source_id",
             "created_by", "posted", "line_account_no", "line_debit", "line_credit", "line_description"],
            [{"entry_no": r.entry_no,
              "description": r.entry_desc,
              "entry_date": r.entry_date.isoformat() if r.entry_date else "",
              "period": r.period,
              "source_type": r.source_type or "",
              "source_id": r.source_id or "",
              "created_by": r.created_by,
              "posted": str(r.posted).lower(),
              "line_account_no": r.account_no,
              "line_debit": r.JournalLine.debit,
              "line_credit": r.JournalLine.credit,
              "line_description": r.JournalLine.description or ""}
             for r in jl_rows],
        )
        print(f"📤 11-accounting.csv: {len(jl_rows)} journal lines")

        # ── AR ──
        result = await db.execute(select(AccountsReceivable))
        ars = result.scalars().all()
        write_csv(
            os.path.join(output_dir, "12-ar.csv"),
            ["customer_name", "invoice_no", "amount", "due_date", "paid_amount", "status"],
            [{"customer_name": ar.customer_name, "invoice_no": ar.invoice_no,
              "amount": ar.amount, "due_date": ar.due_date.isoformat() if ar.due_date else "",
              "paid_amount": ar.paid_amount, "status": ar.status}
             for ar in ars],
        )
        print(f"📤 12-ar.csv: {len(ars)} AR records")

        print(f"\n✅ Export complete → {output_dir}/")


async def cmd_reset(force: bool = False):
    """Reset all data (clear every table)."""
    if not force:
        print("⚠️  This will DELETE ALL DATA in the database.")
        print("   Use --force to confirm.")
        sys.exit(1)

    await init_db()
    async with async_session() as db:
        tables = [
            "dispatch_logs", "operations", "production_orders", "work_centers",
            "capa_records", "non_conformances", "inspection_results", "inspection_orders",
            "journal_lines", "journal_entries", "accounts_receivable", "month_end_closes", "accounts",
            "purchase_order_items", "purchase_orders", "suppliers",
            "bom_items", "products", "parts",
            "inventory_transactions", "inventory",
            "audit_logs",
        ]
        for table in tables:
            await db.execute(text(f"DELETE FROM {table}"))
        await db.commit()
        print(f"✅ All {len(tables)} tables cleared.")


async def cmd_schema():
    """Print all entity schemas (field names and types)."""
    schemas = {
        "parts (01-*.csv)": ["part_no*", "name*", "spec", "unit*", "category"],
        "suppliers (02-*.csv)": ["name*", "contact", "phone", "email", "score"],
        "products (03-*.csv)": ["product_no*", "name*", "description"],
        "work-centers (04-*.csv)": ["name*", "description", "status", "capacity_hours", "efficiency", "location", "alternate_group"],
        "accounts (05-*.csv)": ["account_no*", "name*", "type*", "normal_balance*", "is_active"],
        "inventory (06-*.csv)": ["part_no*", "location", "quantity"],
        "bom (07-*.csv)": ["product_no*", "part_no*", "quantity*", "level*", "sequence_no"],
        "purchase-orders (08-*.csv)": ["po_no*", "supplier_name*", "status", "ordered_by", "notes",
                                       "item_part_no*", "item_quantity*", "item_unit_price", "item_expected_delivery", "item_received_qty"],
        "production-orders (09-*.csv)": ["order_no*", "product_no*", "product_name", "quantity*", "due_date*",
                                         "priority", "status", "notes", "created_by"],
        "quality (10-*.csv)": ["inspection_no*", "part_no*", "po_no", "lot_no", "quantity*",
                               "status", "inspection_date", "inspected_by",
                               "item_no", "item_description", "item_spec_value", "item_measured_value",
                               "item_result", "item_notes"],
        "accounting (11-*.csv)": ["entry_no*", "description*", "entry_date*", "period*", "source_type", "source_id",
                                  "created_by", "posted",
                                  "line_account_no*", "line_debit*", "line_credit*", "line_description"],
        "ar (12-*.csv)": ["customer_name*", "invoice_no*", "amount*", "due_date*", "paid_amount", "status"],
        "dispatch-logs (20-*.csv)": ["order_no", "work_center_name", "action*"],
    }
    print(f"\n{'='*60}")
    print("LLM-ERP Data Schema Reference")
    print(f"{'='*60}")
    print("Fields marked with * are required.\n")
    for entity, fields in schemas.items():
        print(f"  📋 {entity}")
        print(f"     Columns: {', '.join(fields)}")
        print()
    print("Import order follows the numbered prefix (01 → 02 → ... → 12).")
    print("Place CSV files in a directory and run: python -m scripts.manage_data import <dir>/")


# ─── CLI Entry Point ──────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="LLM-ERP Data Management — import, export, reset data"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # import
    imp = sub.add_parser("import", help="Import CSV file(s) into database")
    imp.add_argument("source", help="CSV file or directory of CSV files")
    imp.add_argument("--dry-run", action="store_true", help="Validate only, no DB changes")

    # export
    exp = sub.add_parser("export", help="Export database to CSV files")
    exp.add_argument("output_dir", help="Output directory for CSV files")

    # reset
    rst = sub.add_parser("reset", help="Clear all database tables")
    rst.add_argument("--force", action="store_true", help="Confirm data deletion")

    # schema
    sub.add_parser("schema", help="List all entity schemas and import format")

    args = parser.parse_args()

    if args.command == "import":
        asyncio.run(cmd_import(args.source, dry_run=args.dry_run))
    elif args.command == "export":
        asyncio.run(cmd_export(args.output_dir))
    elif args.command == "reset":
        asyncio.run(cmd_reset(force=args.force))
    elif args.command == "schema":
        asyncio.run(cmd_schema())
