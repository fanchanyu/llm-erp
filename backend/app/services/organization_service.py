"""Organization service — departments, employees, users, roles, permissions, approvals CRUD."""

from __future__ import annotations
import uuid
import hashlib
import secrets
from datetime import datetime, date, timedelta
from typing import Optional
from sqlalchemy import select, or_, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.organization import (
    Department, Employee, User, Role, RolePermission,
    EmployeeRole, ApprovalFlow, ApprovalRequest, ApprovalRecord,
)


# ═══════════════════════════════════════════════════════════════════
# ─── HELPERS ──────────────────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════

def hash_password(password: str) -> str:
    """Simple SHA-256 hash (upgrade to bcrypt/argon2 in production)."""
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password: str, password_hash: str) -> bool:
    return hash_password(password) == password_hash


def generate_token() -> str:
    """Generate a simple session token."""
    return secrets.token_hex(32)


# ═══════════════════════════════════════════════════════════════════
# ─── DEPARTMENT ───────────────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════

async def list_departments(
    db: AsyncSession,
    search: Optional[str] = None,
    status: Optional[str] = None,
    include_tree: bool = False,
) -> list[Department]:
    """List departments with optional search and tree mode."""
    q = select(Department).order_by(Department.level, Department.sort_order, Department.code)
    if search:
        q = q.where(or_(
            Department.code.ilike(f"%{search}%"),
            Department.name.ilike(f"%{search}%"),
        ))
    if status:
        q = q.where(Department.status == status)
    result = await db.execute(q)
    depts = list(result.scalars().all())
    if include_tree:
        return _build_tree(depts)
    return depts


async def list_departments_flat(db: AsyncSession) -> list[Department]:
    """Flat list of all departments."""
    result = await db.execute(select(Department).order_by(Department.level, Department.sort_order, Department.code))
    return list(result.scalars().all())


def _build_tree(depts: list[Department]) -> list[dict]:
    """Build nested tree structure from flat department list."""
    dept_map = {}
    for d in depts:
        info = {
            "id": str(d.id), "code": d.code, "name": d.name,
            "parent_id": str(d.parent_id) if d.parent_id else None,
            "manager_id": str(d.manager_id) if d.manager_id else None,
            "level": d.level, "sort_order": d.sort_order,
            "status": d.status, "description": d.description,
            "children": [],
        }
        dept_map[d.id] = info

    roots = []
    for d_info in dept_map.values():
        if d_info["parent_id"] and d_info["parent_id"] in dept_map:
            parent = dept_map[d_info["parent_id"]]
            parent["children"].append(d_info)
        else:
            roots.append(d_info)
    return roots


async def get_department(db: AsyncSession, dept_id: uuid.UUID) -> Optional[Department]:
    return await db.get(Department, dept_id)


async def get_department_by_code(db: AsyncSession, code: str) -> Optional[Department]:
    result = await db.execute(select(Department).where(Department.code == code))
    return result.scalar_one_or_none()


async def create_department(db: AsyncSession, code: str, name: str, **kwargs) -> Department:
    dept = Department(code=code, name=name, **kwargs)
    db.add(dept)
    await db.flush()
    return dept


async def update_department(db: AsyncSession, dept_id: uuid.UUID, **kwargs) -> Optional[Department]:
    dept = await db.get(Department, dept_id)
    if not dept:
        return None
    for k, v in kwargs.items():
        if v is not None and hasattr(dept, k):
            setattr(dept, k, v)
    dept.updated_at = datetime.utcnow()
    await db.flush()
    return dept


async def delete_department(db: AsyncSession, dept_id: uuid.UUID) -> bool:
    dept = await db.get(Department, dept_id)
    if not dept:
        return False
    # Check for children
    result = await db.execute(select(Department).where(Department.parent_id == dept_id).limit(1))
    if result.scalar_one_or_none():
        raise ValueError("Cannot delete department with child departments")
    await db.delete(dept)
    await db.flush()
    return True


# ═══════════════════════════════════════════════════════════════════
# ─── EMPLOYEE ─────────────────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════

async def list_employees(
    db: AsyncSession,
    search: Optional[str] = None,
    department_code: Optional[str] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
) -> tuple[list[Employee], int]:
    """List employees with search and pagination."""
    q = select(Employee)
    if search:
        q = q.where(or_(
            Employee.employee_no.ilike(f"%{search}%"),
            Employee.name.ilike(f"%{search}%"),
            Employee.email.ilike(f"%{search}%"),
        ))
    if department_code:
        dept = await get_department_by_code(db, department_code)
        if dept:
            q = q.where(Employee.department_id == dept.id)
    if status:
        q = q.where(Employee.status == status)

    count_q = select(func.count()).select_from(q.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    q = q.options(selectinload(Employee.department), selectinload(Employee.manager))
    result = await db.execute(q.order_by(Employee.employee_no).offset(skip).limit(limit))
    return list(result.scalars().all()), total


async def get_employee(db: AsyncSession, emp_id: uuid.UUID) -> Optional[Employee]:
    q = select(Employee).options(
        selectinload(Employee.department), selectinload(Employee.manager)
    ).where(Employee.id == emp_id)
    result = await db.execute(q)
    return result.scalar_one_or_none()


async def get_employee_by_no(db: AsyncSession, employee_no: str) -> Optional[Employee]:
    result = await db.execute(select(Employee).where(Employee.employee_no == employee_no))
    return result.scalar_one_or_none()


async def create_employee(db: AsyncSession, employee_no: str, name: str,
                          department_id: uuid.UUID, **kwargs) -> Employee:
    emp = Employee(employee_no=employee_no, name=name, department_id=department_id, **kwargs)
    db.add(emp)
    await db.flush()
    return emp


async def update_employee(db: AsyncSession, emp_id: uuid.UUID, **kwargs) -> Optional[Employee]:
    emp = await db.get(Employee, emp_id)
    if not emp:
        return None
    for k, v in kwargs.items():
        if v is not None and hasattr(emp, k):
            setattr(emp, k, v)
    emp.updated_at = datetime.utcnow()
    await db.flush()
    # Re-fetch with relationships
    q = select(Employee).options(
        selectinload(Employee.department), selectinload(Employee.manager)
    ).where(Employee.id == emp_id)
    result = await db.execute(q)
    return result.scalar_one_or_none()


# ═══════════════════════════════════════════════════════════════════
# ─── USER ACCOUNT ─────────────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════

async def get_user_by_username(db: AsyncSession, username: str) -> Optional[User]:
    q = select(User).options(selectinload(User.employee)).where(User.username == username)
    result = await db.execute(q)
    return result.scalar_one_or_none()


async def create_user(db: AsyncSession, username: str, password: str,
                      employee_id: uuid.UUID) -> User:
    user = User(
        username=username,
        password_hash=hash_password(password),
        employee_id=employee_id,
    )
    db.add(user)
    await db.flush()
    return user


async def authenticate(db: AsyncSession, username: str, password: str) -> Optional[dict]:
    """Authenticate user. Returns user info with roles/permissions or None."""
    user = await get_user_by_username(db, username)
    if not user:
        return None
    if user.status != "active":
        return None
    # Check lock
    if user.locked_until and user.locked_until > datetime.utcnow():
        return None
    if not verify_password(password, user.password_hash):
        user.login_attempts = (user.login_attempts or 0) + 1
        if user.login_attempts >= 5:
            user.locked_until = datetime.utcnow() + timedelta(minutes=15)
        await db.flush()
        return None
    # Success — reset attempts
    user.login_attempts = 0
    user.locked_until = None
    user.last_login = datetime.utcnow()
    await db.flush()

    # Get roles and permissions
    roles = await get_employee_roles(db, user.employee_id)
    perms = await get_employee_permissions(db, user.employee_id)

    # Create auth session token
    from app.auth import create_session_token
    token = create_session_token(user.employee_id, user.username, roles, perms)

    return {
        "token": token,
        "user": user,
        "roles": roles,
        "permissions": perms,
    }


# ═══════════════════════════════════════════════════════════════════
# ─── ROLE ─────────────────────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════

async def list_roles(db: AsyncSession) -> list[Role]:
    result = await db.execute(select(Role).order_by(Role.level.desc(), Role.code))
    return list(result.scalars().all())


async def get_role_by_code(db: AsyncSession, code: str) -> Optional[Role]:
    result = await db.execute(select(Role).where(Role.code == code))
    return result.scalar_one_or_none()


async def create_role(db: AsyncSession, name: str, code: str, **kwargs) -> Role:
    role = Role(name=name, code=code, **kwargs)
    db.add(role)
    await db.flush()
    return role


# ═══════════════════════════════════════════════════════════════════
# ─── PERMISSION ───────────────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════

async def get_role_permissions(db: AsyncSession, role_id: uuid.UUID) -> list[RolePermission]:
    result = await db.execute(select(RolePermission).where(RolePermission.role_id == role_id))
    return list(result.scalars().all())


async def get_employee_permissions(db: AsyncSession, employee_id: uuid.UUID) -> list[dict]:
    """Aggregate all permissions for an employee across their roles."""
    er_result = await db.execute(
        select(EmployeeRole.role_id).where(EmployeeRole.employee_id == employee_id)
    )
    role_ids = [r[0] for r in er_result.all()]
    if not role_ids:
        return []

    perm_result = await db.execute(
        select(RolePermission).where(RolePermission.role_id.in_(role_ids))
    )
    perms = perm_result.scalars().all()

    # Deduplicate: same module+action takes the broadest scope
    seen = {}
    for p in perms:
        key = (p.module, p.action)
        if key not in seen or _scope_weight(p.scope) > _scope_weight(seen[key].scope):
            seen[key] = p

    # Enrich with role info
    roles_result = await db.execute(select(Role))
    role_map = {r.id: r for r in roles_result.scalars().all()}
    result = []
    for p in seen.values():
        role = role_map.get(p.role_id)
        result.append({
            "module": p.module,
            "action": p.action,
            "scope": p.scope,
            "role_code": role.code if role else None,
            "role_name": role.name if role else None,
        })
    return result


def _scope_weight(scope: str) -> int:
    return {"self": 0, "department": 1, "all": 2}.get(scope, 0)


async def set_permission(db: AsyncSession, role_id: uuid.UUID, module: str,
                         action: str, scope: str = "department") -> RolePermission:
    """Set or update a single permission."""
    result = await db.execute(
        select(RolePermission).where(
            RolePermission.role_id == role_id,
            RolePermission.module == module,
            RolePermission.action == action,
        )
    )
    perm = result.scalar_one_or_none()
    if perm:
        perm.scope = scope
    else:
        perm = RolePermission(role_id=role_id, module=module, action=action, scope=scope)
        db.add(perm)
    await db.flush()
    return perm


async def remove_permission(db: AsyncSession, perm_id: uuid.UUID) -> bool:
    perm = await db.get(RolePermission, perm_id)
    if not perm:
        return False
    await db.delete(perm)
    await db.flush()
    return True


# ═══════════════════════════════════════════════════════════════════
# ─── EMPLOYEE ROLE ASSIGNMENT ─────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════

async def get_employee_roles(db: AsyncSession, employee_id: uuid.UUID) -> list[dict]:
    """Get all roles assigned to an employee."""
    q = select(EmployeeRole, Role).join(Role, EmployeeRole.role_id == Role.id).where(
        EmployeeRole.employee_id == employee_id
    )
    result = await db.execute(q)
    return [
        {"role_code": r.Role.code, "role_name": r.Role.name, "level": r.Role.level}
        for r in result.all()
    ]


async def assign_role(db: AsyncSession, employee_id: uuid.UUID, role_id: uuid.UUID,
                      assigned_by: Optional[uuid.UUID] = None) -> EmployeeRole:
    er = EmployeeRole(employee_id=employee_id, role_id=role_id, assigned_by=assigned_by)
    db.add(er)
    await db.flush()
    return er


async def remove_employee_role(db: AsyncSession, er_id: uuid.UUID) -> bool:
    er = await db.get(EmployeeRole, er_id)
    if not er:
        return False
    await db.delete(er)
    await db.flush()
    return True


# ═══════════════════════════════════════════════════════════════════
# ─── APPROVAL FLOW ────────────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════

async def list_approval_flows(db: AsyncSession, module: Optional[str] = None) -> list[ApprovalFlow]:
    q = select(ApprovalFlow).order_by(ApprovalFlow.module, ApprovalFlow.name)
    if module:
        q = q.where(ApprovalFlow.module == module)
    result = await db.execute(q)
    return list(result.scalars().all())


async def create_approval_flow(db: AsyncSession, name: str, module: str,
                                trigger_event: str, steps: list[dict], **kwargs) -> ApprovalFlow:
    flow = ApprovalFlow(name=name, module=module, trigger_event=trigger_event, steps=steps, **kwargs)
    db.add(flow)
    await db.flush()
    return flow


# ═══════════════════════════════════════════════════════════════════
# ─── APPROVAL REQUEST ─────────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════

async def create_approval_request(db: AsyncSession, flow_id: uuid.UUID,
                                   request_type: str, request_ref_id: uuid.UUID,
                                   requester_id: uuid.UUID, **kwargs) -> ApprovalRequest:
    req = ApprovalRequest(
        flow_id=flow_id, request_type=request_type, request_ref_id=request_ref_id,
        requester_id=requester_id, current_step=1, status="pending", **kwargs,
    )
    db.add(req)
    await db.flush()
    return req


async def list_pending_approvals(db: AsyncSession, approver_employee_id: uuid.UUID) -> list[dict]:
    """Get pending approval requests for an employee (based on their roles)."""
    roles = await get_employee_roles(db, approver_employee_id)
    role_codes = [r["role_code"] for r in roles]

    # Find flows where one of the user's roles can approve at current_step
    flows_result = await db.execute(select(ApprovalFlow).where(ApprovalFlow.status == "active"))
    flows = list(flows_result.scalars().all())

    # Build a list of matching flow IDs
    flow_ids = []
    for f in flows:
        for step in (f.steps or []):
            if step.get("approver_role") in role_codes:
                flow_ids.append(f.id)
                break

    if not flow_ids:
        return []

    q = select(ApprovalRequest).options(
        selectinload(ApprovalRequest.flow),
        selectinload(ApprovalRequest.requester),
    ).where(
        ApprovalRequest.flow_id.in_(flow_ids),
        ApprovalRequest.status == "pending",
    ).order_by(ApprovalRequest.created_at.desc())
    result = await db.execute(q)
    requests = list(result.scalars().all())

    # Filter: only requests where the current_step matches the user's role
    filtered = []
    for req in requests:
        flow = req.flow
        if not flow or not flow.steps:
            continue
        current_step_def = None
        for s in flow.steps:
            if s.get("step") == req.current_step:
                current_step_def = s
                break
        if current_step_def and current_step_def.get("approver_role") in role_codes:
            filtered.append({
                "id": str(req.id),
                "flow_name": flow.name,
                "request_type": req.request_type,
                "request_ref_no": req.request_ref_no,
                "requester_name": req.requester.name if req.requester else None,
                "current_step": req.current_step,
                "status": req.status,
                "created_at": req.created_at,
            })

    return filtered


async def approve_or_reject(db: AsyncSession, request_id: uuid.UUID,
                             approver_id: uuid.UUID, action: str,
                             comment: Optional[str] = None) -> Optional[dict]:
    """Approve or reject an approval request. Returns updated request info."""
    req = await db.get(ApprovalRequest, request_id)
    if not req or req.status != "pending":
        return None

    # Record the action
    record = ApprovalRecord(
        request_id=request_id, step=req.current_step,
        approver_id=approver_id, action=action, comment=comment,
    )
    db.add(record)

    if action == "rejected":
        req.status = "rejected"
    elif action == "approved":
        # Check if there are more steps
        flow = await db.get(ApprovalFlow, req.flow_id)
        if flow and flow.steps:
            next_step = req.current_step + 1
            # Find the step definition to confirm it exists
            step_exists = any(s.get("step") == next_step for s in flow.steps)
            if step_exists:
                req.current_step = next_step
            else:
                req.status = "approved"

    req.updated_at = datetime.utcnow()
    await db.flush()
    return {"id": str(req.id), "status": req.status, "current_step": req.current_step}


async def get_approval_history(db: AsyncSession, request_id: uuid.UUID) -> list[ApprovalRecord]:
    q = select(ApprovalRecord).options(
        selectinload(ApprovalRecord.approver)
    ).where(
        ApprovalRecord.request_id == request_id
    ).order_by(ApprovalRecord.step)
    result = await db.execute(q)
    return list(result.scalars().all())


# ═══════════════════════════════════════════════════════════════════
# ─── SEED DATA ────────────────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════

async def seed_organization(db: AsyncSession):
    """Seed default departments, roles, permissions, and sample employees."""

    # ── Departments ──
    depts = {}
    seed_depts = [
        ("HQ", "總公司", None, 1),
        ("FACTORY", "製造廠", "HQ", 2),
        ("ADMIN", "管理部", "HQ", 3),
        ("IT", "資訊課", "ADMIN", 4),
        ("HR", "人事課", "ADMIN", 4),
        ("FINANCE", "財務課", "ADMIN", 4),
        ("SALES", "業務部", "HQ", 3),
        ("PURCHASE", "採購課", "FACTORY", 4),
        ("WAREHOUSE", "倉管課", "FACTORY", 4),
        ("PRODUCE", "製造課", "FACTORY", 4),
        ("QA", "品管課", "FACTORY", 4),
        ("ENGINEER", "工程課", "FACTORY", 4),
    ]
    for code, name, parent_code, level in seed_depts:
        parent_id = depts.get(parent_code + "_id") if parent_code else None
        dept = Department(code=code, name=name, parent_id=parent_id, level=level)
        db.add(dept)
        await db.flush()
        depts[code + "_id"] = dept.id

    # ── Employees ──
    emp_records = [
        ("E001", "張總", "gm@factory.com", "廠長", "HQ"),
        ("E002", "王經理", "manager@factory.com", "經理", "FACTORY"),
        ("E003", "李課長", "it@factory.com", "課長", "IT"),
        ("E004", "陳採購", "purchase@factory.com", "採購專員", "PURCHASE"),
        ("E005", "林倉管", "warehouse@factory.com", "倉管員", "WAREHOUSE"),
        ("E006", "黃工程", "engineer@factory.com", "工程師", "ENGINEER"),
        ("E007", "周品管", "qa@factory.com", "品管員", "QA"),
        ("E008", "吳業務", "sales@factory.com", "業務專員", "SALES"),
        ("E009", "劉會計", "finance@factory.com", "會計", "FINANCE"),
        ("E010", "鄭人事", "hr@factory.com", "人事專員", "HR"),
    ]
    for eno, name, email, title, dept_code in emp_records:
        emp = Employee(
            employee_no=eno, name=name, email=email, title=title,
            department_id=depts[dept_code + "_id"],
            hire_date=date(2025, 1, 1),
        )
        db.add(emp)
        await db.flush()
        depts["emp:" + eno] = emp.id

    # ── Set department managers ──
    await db.execute(
        select(Department)
    )
    # Update managers
    hq_dept = await get_department_by_code(db, "HQ")
    factory_dept = await get_department_by_code(db, "FACTORY")
    it_dept = await get_department_by_code(db, "IT")
    if hq_dept:
        hq_dept.manager_id = depts.get("emp:E001")
    if factory_dept:
        factory_dept.manager_id = depts.get("emp:E002")
    if it_dept:
        it_dept.manager_id = depts.get("emp:E003")

    # ── Roles ──
    role_records = [
        ("operator", "操作員", 1),
        ("clerk", "專員", 2),
        ("section_chief", "課長", 3),
        ("manager", "經理", 4),
        ("plant_manager", "廠長", 5),
        ("admin", "系統管理員", 99),
    ]
    roles = {}
    for code, name, level in role_records:
        r = Role(code=code, name=name, level=level)
        db.add(r)
        await db.flush()
        roles[code] = r.id

    # ── Role Permissions ──
    modules = ["inventory", "purchase", "bom", "dispatch", "quality",
               "accounting", "customer", "lead", "opportunity", "contract",
               "report", "organization", "approval"]

    # admin: everything
    for mod in modules:
        for act in ["create", "read", "update", "delete", "approve"]:
            db.add(RolePermission(role_id=roles["admin"], module=mod, action=act, scope="all"))

    # plant_manager: read all, write most, approve all
    for mod in modules:
        for act in ["create", "read", "update", "approve"]:
            db.add(RolePermission(role_id=roles["plant_manager"], module=mod, action=act, scope="all"))
        db.add(RolePermission(role_id=roles["plant_manager"], module=mod, action="delete", scope="department"))

    # manager: read+write department, approve department
    for mod in modules:
        if mod in ("organization", "approval"):
            db.add(RolePermission(role_id=roles["manager"], module=mod, action="read", scope="department"))
        else:
            for act in ["create", "read", "update"]:
                db.add(RolePermission(role_id=roles["manager"], module=mod, action=act, scope="department"))
            db.add(RolePermission(role_id=roles["manager"], module=mod, action="approve", scope="department"))

    # section_chief: read department, write limited
    for mod in modules:
        if mod in ("purchase", "inventory", "dispatch", "quality", "customer", "report"):
            db.add(RolePermission(role_id=roles["section_chief"], module=mod, action="read", scope="department"))
            db.add(RolePermission(role_id=roles["section_chief"], module=mod, action="create", scope="department"))
            db.add(RolePermission(role_id=roles["section_chief"], module=mod, action="update", scope="department"))

    # clerk: read+create own department, update own records
    for mod in modules:
        if mod in ("purchase", "inventory", "customer", "lead", "opportunity"):
            db.add(RolePermission(role_id=roles["clerk"], module=mod, action="read", scope="department"))
            db.add(RolePermission(role_id=roles["clerk"], module=mod, action="create", scope="department"))

    # operator: read only
    for mod in ["inventory", "dispatch", "quality"]:
        db.add(RolePermission(role_id=roles["operator"], module=mod, action="read", scope="self"))

    # ── Employee Role Assignments ──
    assignments = [
        ("E001", "plant_manager"), ("E002", "manager"), ("E003", "section_chief"),
        ("E004", "clerk"), ("E005", "clerk"), ("E006", "clerk"),
        ("E007", "clerk"), ("E008", "clerk"), ("E009", "clerk"), ("E010", "clerk"),
    ]
    for eno, rcode in assignments:
        if "emp:" + eno in depts and rcode in roles:
            db.add(EmployeeRole(
                employee_id=depts["emp:" + eno],
                role_id=roles[rcode],
            ))

    # Admin role for E001 (張總) and E003 (李課長)
    db.add(EmployeeRole(employee_id=depts["emp:E001"], role_id=roles["admin"]))
    db.add(EmployeeRole(employee_id=depts["emp:E003"], role_id=roles["admin"]))

    # ── Users (default password: "123456") ──
    users_data = [
        ("admin", "123456", "E001"),
        ("manager", "123456", "E002"),
        ("itchief", "123456", "E003"),
        ("purchaser", "123456", "E004"),
        ("warehouse", "123456", "E005"),
        ("engineer", "123456", "E006"),
        ("qa", "123456", "E007"),
        ("sales", "123456", "E008"),
        ("finance", "123456", "E009"),
        ("hr", "123456", "E010"),
    ]
    for uname, pwd, eno in users_data:
        if "emp:" + eno in depts:
            db.add(User(
                username=uname,
                password_hash=hash_password(pwd),
                employee_id=depts["emp:" + eno],
            ))

    # ── Approval Flows ──
    sample_flows = [
        ("採購單簽核", "purchase", "purchase_order_created", [
            {"step": 1, "approver_role": "section_chief", "auto_escalate_min": 480},
            {"step": 2, "approver_role": "manager", "auto_escalate_min": 240},
            {"step": 3, "approver_role": "plant_manager"},
        ]),
        ("報價單簽核", "customer", "quotation_created", [
            {"step": 1, "approver_role": "manager"},
            {"step": 2, "approver_role": "plant_manager"},
        ]),
        ("品質異常簽核", "quality", "ncr_created", [
            {"step": 1, "approver_role": "section_chief"},
            {"step": 2, "approver_role": "manager"},
        ]),
    ]
    for name, mod, evt, steps in sample_flows:
        db.add(ApprovalFlow(name=name, module=mod, trigger_event=evt, steps=steps))

    await db.flush()
