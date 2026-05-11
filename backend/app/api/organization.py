"""Organization API — departments, employees, users, roles, permissions, approvals."""

import uuid
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.services import organization_service as svc
from app.schemas.organization import (
    DepartmentCreate, DepartmentUpdate, DepartmentResponse,
    EmployeeCreate, EmployeeUpdate, EmployeeResponse,
    UserCreate, UserResponse, LoginRequest, LoginResponse,
    RoleCreate, RoleResponse,
    PermissionCreate, PermissionResponse,
    EmployeeRoleCreate, EmployeeRoleResponse,
    ApprovalFlowCreate, ApprovalFlowResponse,
    ApprovalRequestResponse, ApprovalAction, ApprovalRecordResponse,
)

router = APIRouter(prefix="/org", tags=["organization"])


# ═══════════════════════════════════════════════════════════════════
# ─── DEPARTMENT ───────────────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════

@router.get("/departments", response_model=dict)
async def list_departments(
    search: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    tree: bool = Query(False, description="Return as nested tree"),
    db: AsyncSession = Depends(get_db),
):
    """List departments. Use ?tree=true for nested org tree."""
    depts = await svc.list_departments(db, search, status, include_tree=tree)

    if tree:
        # _build_tree already returns full dicts
        return {"departments": depts, "total": len(depts)}

    items = [
        DepartmentResponse(
            id=str(d.id), code=d.code, name=d.name,
            parent_id=str(d.parent_id) if d.parent_id else None,
            manager_id=str(d.manager_id) if d.manager_id else None,
            level=d.level, sort_order=d.sort_order, status=d.status,
            description=d.description,
            created_at=d.created_at, updated_at=d.updated_at,
        )
        for d in depts
    ]

    return {"departments": items, "total": len(items)}


@router.get("/departments/{dept_id}", response_model=DepartmentResponse)
async def get_department(dept_id: str, db: AsyncSession = Depends(get_db)):
    dept = await svc.get_department(db, uuid.UUID(dept_id))
    if not dept:
        raise HTTPException(404, "Department not found")
    return DepartmentResponse(
        id=str(dept.id), code=dept.code, name=dept.name,
        parent_id=str(dept.parent_id) if dept.parent_id else None,
        manager_id=str(dept.manager_id) if dept.manager_id else None,
        level=dept.level, sort_order=dept.sort_order, status=dept.status,
        description=dept.description,
        created_at=dept.created_at, updated_at=dept.updated_at,
    )


@router.post("/departments", response_model=DepartmentResponse, status_code=201)
async def create_department(data: DepartmentCreate, db: AsyncSession = Depends(get_db)):
    existing = await svc.get_department_by_code(db, data.code)
    if existing:
        raise HTTPException(400, f"Department code {data.code} already exists")

    parent_id = uuid.UUID(data.parent_id) if data.parent_id else None
    dept = await svc.create_department(
        db, data.code, data.name,
        parent_id=parent_id, level=data.level,
        sort_order=data.sort_order, status=data.status,
        description=data.description,
    )
    return DepartmentResponse(
        id=str(dept.id), code=dept.code, name=dept.name,
        parent_id=str(dept.parent_id) if dept.parent_id else None,
        manager_id=None, level=dept.level,
        sort_order=dept.sort_order, status=dept.status,
        description=dept.description,
        created_at=dept.created_at, updated_at=dept.updated_at,
    )


@router.put("/departments/{dept_id}", response_model=DepartmentResponse)
async def update_department(dept_id: str, data: DepartmentUpdate, db: AsyncSession = Depends(get_db)):
    kwargs = {}
    for field in ["name", "level", "sort_order", "status", "description"]:
        if getattr(data, field, None) is not None:
            kwargs[field] = getattr(data, field)
    if data.parent_id is not None:
        kwargs["parent_id"] = uuid.UUID(data.parent_id)
    if data.manager_id is not None:
        kwargs["manager_id"] = uuid.UUID(data.manager_id)

    dept = await svc.update_department(db, uuid.UUID(dept_id), **kwargs)
    if not dept:
        raise HTTPException(404, "Department not found")
    return DepartmentResponse(
        id=str(dept.id), code=dept.code, name=dept.name,
        parent_id=str(dept.parent_id) if dept.parent_id else None,
        manager_id=str(dept.manager_id) if dept.manager_id else None,
        level=dept.level, sort_order=dept.sort_order, status=dept.status,
        description=dept.description,
        created_at=dept.created_at, updated_at=dept.updated_at,
    )


@router.delete("/departments/{dept_id}", response_model=dict)
async def delete_department(dept_id: str, db: AsyncSession = Depends(get_db)):
    try:
        ok = await svc.delete_department(db, uuid.UUID(dept_id))
    except ValueError as e:
        raise HTTPException(400, str(e))
    if not ok:
        raise HTTPException(404, "Department not found")
    return {"message": "Department deleted"}


# ═══════════════════════════════════════════════════════════════════
# ─── EMPLOYEE ─────────────────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════

@router.get("/employees", response_model=dict)
async def list_employees(
    search: Optional[str] = Query(None),
    department_code: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    employees, total = await svc.list_employees(db, search, department_code, status, skip, limit)
    items = [
        EmployeeResponse(
            id=str(e.id), employee_no=e.employee_no, name=e.name,
            email=e.email, phone=e.phone, title=e.title,
            department_id=str(e.department_id) if e.department_id else None,
            department_name=e.department.name if e.department else None,
            manager_id=str(e.manager_id) if e.manager_id else None,
            manager_name=e.manager.name if e.manager else None,
            hire_date=e.hire_date.isoformat() if e.hire_date else None,
            status=e.status,
            created_at=e.created_at,
        )
        for e in employees
    ]
    return {"employees": items, "total": total}


@router.get("/employees/{emp_id}", response_model=EmployeeResponse)
async def get_employee(emp_id: str, db: AsyncSession = Depends(get_db)):
    emp = await svc.get_employee(db, uuid.UUID(emp_id))
    if not emp:
        raise HTTPException(404, "Employee not found")
    return EmployeeResponse(
        id=str(emp.id), employee_no=emp.employee_no, name=emp.name,
        email=emp.email, phone=emp.phone, title=emp.title,
        department_id=str(emp.department_id) if emp.department_id else None,
        department_name=emp.department.name if emp.department else None,
        manager_id=str(emp.manager_id) if emp.manager_id else None,
        manager_name=emp.manager.name if emp.manager else None,
        hire_date=emp.hire_date.isoformat() if emp.hire_date else None,
        status=emp.status,
        created_at=emp.created_at,
    )


@router.post("/employees", response_model=EmployeeResponse, status_code=201)
async def create_employee(data: EmployeeCreate, db: AsyncSession = Depends(get_db)):
    existing = await svc.get_employee_by_no(db, data.employee_no)
    if existing:
        raise HTTPException(400, f"Employee {data.employee_no} already exists")

    dept = await svc.get_department_by_code(db, data.department_code)
    if not dept:
        raise HTTPException(400, f"Department not found: {data.department_code}")

    kwargs = {"email": data.email, "phone": data.phone, "title": data.title}
    if data.manager_id:
        kwargs["manager_id"] = uuid.UUID(data.manager_id)
    if data.hire_date:
        kwargs["hire_date"] = datetime.fromisoformat(data.hire_date).date()

    emp = await svc.create_employee(db, data.employee_no, data.name, dept.id, **kwargs)
    return EmployeeResponse(
        id=str(emp.id), employee_no=emp.employee_no, name=emp.name,
        email=emp.email, phone=emp.phone, title=emp.title,
        department_id=str(emp.department_id),
        department_name=dept.name,
        status=emp.status,
        created_at=emp.created_at,
    )


@router.put("/employees/{emp_id}", response_model=EmployeeResponse)
async def update_employee(emp_id: str, data: EmployeeUpdate, db: AsyncSession = Depends(get_db)):
    kwargs = {}
    for field in ["name", "email", "phone", "title", "status"]:
        if getattr(data, field, None) is not None:
            kwargs[field] = getattr(data, field)
    if data.department_code is not None:
        dept = await svc.get_department_by_code(db, data.department_code)
        if not dept:
            raise HTTPException(400, f"Department not found: {data.department_code}")
        kwargs["department_id"] = dept.id
    if data.manager_id is not None:
        kwargs["manager_id"] = uuid.UUID(data.manager_id)
    if data.hire_date is not None:
        kwargs["hire_date"] = datetime.fromisoformat(data.hire_date).date()

    emp = await svc.update_employee(db, uuid.UUID(emp_id), **kwargs)
    if not emp:
        raise HTTPException(404, "Employee not found")
    return EmployeeResponse(
        id=str(emp.id), employee_no=emp.employee_no, name=emp.name,
        email=emp.email, phone=emp.phone, title=emp.title,
        department_id=str(emp.department_id) if emp.department_id else None,
        department_name=emp.department.name if emp.department else None,
        manager_id=str(emp.manager_id) if emp.manager_id else None,
        manager_name=emp.manager.name if emp.manager else None,
        hire_date=emp.hire_date.isoformat() if emp.hire_date else None,
        status=emp.status,
        created_at=emp.created_at,
    )


# ═══════════════════════════════════════════════════════════════════
# ─── USER ACCOUNT ─────────────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════

@router.post("/users", response_model=UserResponse, status_code=201)
async def create_user(data: UserCreate, db: AsyncSession = Depends(get_db)):
    existing_user = await svc.get_user_by_username(db, data.username)
    if existing_user:
        raise HTTPException(400, f"Username {data.username} already exists")

    emp = await svc.get_employee_by_no(db, data.employee_no)
    if not emp:
        raise HTTPException(400, f"Employee not found: {data.employee_no}")

    user = await svc.create_user(db, data.username, data.password, emp.id)
    return UserResponse(
        id=str(user.id), username=user.username,
        employee_id=str(user.employee_id),
        employee_name=emp.name,
        status=user.status,
        created_at=user.created_at,
    )


@router.post("/login", response_model=LoginResponse)
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await svc.authenticate(db, data.username, data.password)
    if not result:
        raise HTTPException(401, "Invalid credentials or account locked")

    user = result["user"]
    return LoginResponse(
        token=result["token"],
        user=UserResponse(
            id=str(user.id), username=user.username,
            employee_id=str(user.employee_id),
            employee_name=user.employee.name if user.employee else None,
            last_login=user.last_login,
            status=user.status,
            created_at=user.created_at,
        ),
        roles=result["roles"],
        permissions=result["permissions"],
    )


# ═══════════════════════════════════════════════════════════════════
# ─── ROLE ─────────────────────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════

@router.get("/roles", response_model=dict)
async def list_roles(db: AsyncSession = Depends(get_db)):
    roles = await svc.list_roles(db)
    items = [
        RoleResponse(
            id=str(r.id), name=r.name, code=r.code,
            description=r.description, level=r.level,
            created_at=r.created_at,
        )
        for r in roles
    ]
    return {"roles": items, "total": len(items)}


@router.post("/roles", response_model=RoleResponse, status_code=201)
async def create_role(data: RoleCreate, db: AsyncSession = Depends(get_db)):
    existing = await svc.get_role_by_code(db, data.code)
    if existing:
        raise HTTPException(400, f"Role code {data.code} already exists")
    role = await svc.create_role(db, data.name, data.code, description=data.description, level=data.level)
    return RoleResponse(
        id=str(role.id), name=role.name, code=role.code,
        description=role.description, level=role.level,
        created_at=role.created_at,
    )


# ═══════════════════════════════════════════════════════════════════
# ─── PERMISSION ───────────────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════

@router.get("/permissions", response_model=dict)
async def list_permissions(
    role_code: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    if role_code:
        role = await svc.get_role_by_code(db, role_code)
        if not role:
            raise HTTPException(404, f"Role not found: {role_code}")
        perms = await svc.get_role_permissions(db, role.id)
        role_map = {role.id: role}
    else:
        roles = await svc.list_roles(db)
        role_map = {r.id: r for r in roles}
        perms = []
        for r in roles:
            perms.extend(await svc.get_role_permissions(db, r.id))

    items = [
        PermissionResponse(
            id=str(p.id),
            role_code=role_map[p.role_id].code if p.role_id in role_map else None,
            role_name=role_map[p.role_id].name if p.role_id in role_map else None,
            module=p.module, action=p.action, scope=p.scope,
        )
        for p in perms
    ]
    return {"permissions": items, "total": len(items)}


@router.post("/permissions", response_model=dict, status_code=201)
async def set_permission(data: PermissionCreate, db: AsyncSession = Depends(get_db)):
    role = await svc.get_role_by_code(db, data.role_code)
    if not role:
        raise HTTPException(404, f"Role not found: {data.role_code}")
    perm = await svc.set_permission(db, role.id, data.module, data.action, data.scope)
    return {
        "id": str(perm.id),
        "role_code": data.role_code,
        "module": perm.module,
        "action": perm.action,
        "scope": perm.scope,
        "message": "Permission set",
    }


# ═══════════════════════════════════════════════════════════════════
# ─── EMPLOYEE ROLE ASSIGNMENT ─────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════

@router.get("/employee-roles/{emp_id}", response_model=dict)
async def get_employee_roles(emp_id: str, db: AsyncSession = Depends(get_db)):
    emp = await svc.get_employee(db, uuid.UUID(emp_id))
    if not emp:
        raise HTTPException(404, "Employee not found")
    roles = await svc.get_employee_roles(db, uuid.UUID(emp_id))
    return {"employee_id": emp_id, "roles": roles}


@router.post("/employee-roles", response_model=dict, status_code=201)
async def assign_role(data: EmployeeRoleCreate, db: AsyncSession = Depends(get_db)):
    emp = await svc.get_employee_by_no(db, data.employee_no)
    if not emp:
        raise HTTPException(404, f"Employee not found: {data.employee_no}")
    role = await svc.get_role_by_code(db, data.role_code)
    if not role:
        raise HTTPException(404, f"Role not found: {data.role_code}")
    er = await svc.assign_role(db, emp.id, role.id)
    return {
        "id": str(er.id),
        "employee_no": data.employee_no,
        "role_code": data.role_code,
        "message": "Role assigned",
    }


# ═══════════════════════════════════════════════════════════════════
# ─── APPROVAL FLOW ────────────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════

@router.get("/approval-flows", response_model=dict)
async def list_approval_flows(
    module: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    flows = await svc.list_approval_flows(db, module)
    items = [
        ApprovalFlowResponse(
            id=str(f.id), name=f.name, module=f.module,
            trigger_event=f.trigger_event, description=f.description,
            steps=f.steps, status=f.status,
            created_at=f.created_at,
        )
        for f in flows
    ]
    return {"approval_flows": items, "total": len(items)}


@router.post("/approval-flows", response_model=ApprovalFlowResponse, status_code=201)
async def create_approval_flow(data: ApprovalFlowCreate, db: AsyncSession = Depends(get_db)):
    steps = [s.model_dump() for s in data.steps]
    flow = await svc.create_approval_flow(
        db, data.name, data.module, data.trigger_event, steps,
        description=data.description,
    )
    return ApprovalFlowResponse(
        id=str(flow.id), name=flow.name, module=flow.module,
        trigger_event=flow.trigger_event, description=flow.description,
        steps=flow.steps, status=flow.status,
        created_at=flow.created_at,
    )


# ═══════════════════════════════════════════════════════════════════
# ─── APPROVAL REQUEST & RECORD ────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════

@router.get("/approvals/pending/{emp_id}", response_model=dict)
async def get_pending_approvals(emp_id: str, db: AsyncSession = Depends(get_db)):
    """Get pending approval requests for an employee."""
    items = await svc.list_pending_approvals(db, uuid.UUID(emp_id))
    return {"approvals": items, "total": len(items)}


@router.get("/approvals/history/{request_id}", response_model=dict)
async def get_approval_history(request_id: str, db: AsyncSession = Depends(get_db)):
    records = await svc.get_approval_history(db, uuid.UUID(request_id))
    items = [
        ApprovalRecordResponse(
            id=str(r.id), step=r.step,
            approver_name=r.approver.name if r.approver else None,
            action=r.action, comment=r.comment,
            created_at=r.created_at,
        )
        for r in records
    ]
    return {"records": items, "total": len(items)}


@router.post("/approvals/{request_id}/action", response_model=dict)
async def approve_or_reject(
    request_id: str, data: ApprovalAction,
    emp_id: str = Query(..., description="Approver employee ID"),
    db: AsyncSession = Depends(get_db),
):
    result = await svc.approve_or_reject(
        db, uuid.UUID(request_id), uuid.UUID(emp_id),
        data.action, data.comment,
    )
    if not result:
        raise HTTPException(400, "Cannot process: request not found or already processed")
    return result
