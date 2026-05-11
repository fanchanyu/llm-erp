"""Pydantic schemas for Organization API — departments, employees, users, roles, permissions, approvals."""

from datetime import datetime, date
from typing import Optional
from pydantic import BaseModel, Field


# ─── Department ───────────────────────────────────────────────────

class DepartmentCreate(BaseModel):
    code: str = Field(..., min_length=1, max_length=20)
    name: str = Field(..., min_length=1, max_length=200)
    parent_id: Optional[str] = None
    level: Optional[int] = 1
    sort_order: Optional[int] = 0
    status: Optional[str] = "active"
    description: Optional[str] = None


class DepartmentUpdate(BaseModel):
    name: Optional[str] = None
    parent_id: Optional[str] = None
    manager_id: Optional[str] = None
    level: Optional[int] = None
    sort_order: Optional[int] = None
    status: Optional[str] = None
    description: Optional[str] = None


class DepartmentResponse(BaseModel):
    id: str
    code: str
    name: str
    parent_id: Optional[str] = None
    manager_id: Optional[str] = None
    level: int
    sort_order: int
    status: str
    description: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    children: Optional[list] = None  # nested children for tree view


# ─── Employee ─────────────────────────────────────────────────────

class EmployeeCreate(BaseModel):
    employee_no: str = Field(..., min_length=1, max_length=20)
    name: str = Field(..., min_length=1, max_length=100)
    email: Optional[str] = None
    phone: Optional[str] = None
    title: Optional[str] = None
    department_code: str = Field(..., min_length=1)  # department code (natural key)
    manager_id: Optional[str] = None
    hire_date: Optional[str] = None  # ISO date string


class EmployeeUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    title: Optional[str] = None
    department_code: Optional[str] = None
    manager_id: Optional[str] = None
    hire_date: Optional[str] = None
    status: Optional[str] = None


class EmployeeResponse(BaseModel):
    id: str
    employee_no: str
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    title: Optional[str] = None
    department_id: Optional[str] = None
    department_name: Optional[str] = None
    manager_id: Optional[str] = None
    manager_name: Optional[str] = None
    hire_date: Optional[str] = None
    status: str
    created_at: Optional[datetime] = None


# ─── User Account ─────────────────────────────────────────────────

class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6, max_length=100)
    employee_no: str = Field(..., min_length=1)  # link to existing employee


class UserResponse(BaseModel):
    id: str
    username: str
    employee_id: str
    employee_name: Optional[str] = None
    last_login: Optional[datetime] = None
    status: str
    created_at: Optional[datetime] = None


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    token: str
    user: UserResponse
    roles: list[dict]
    permissions: list[dict]


# ─── Role ─────────────────────────────────────────────────────────

class RoleCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    code: str = Field(..., min_length=1, max_length=50)
    description: Optional[str] = None
    level: Optional[int] = 1


class RoleResponse(BaseModel):
    id: str
    name: str
    code: str
    description: Optional[str] = None
    level: int
    created_at: Optional[datetime] = None


# ─── Permission ───────────────────────────────────────────────────

class PermissionCreate(BaseModel):
    role_code: str
    module: str
    action: str  # create, read, update, delete, approve
    scope: Optional[str] = "department"  # all, department, self


class PermissionResponse(BaseModel):
    id: str
    role_code: Optional[str] = None
    role_name: Optional[str] = None
    module: str
    action: str
    scope: str


# ─── Employee Role Assignment ─────────────────────────────────────

class EmployeeRoleCreate(BaseModel):
    employee_no: str
    role_code: str
    expires_at: Optional[str] = None


class EmployeeRoleResponse(BaseModel):
    id: str
    employee_no: Optional[str] = None
    employee_name: Optional[str] = None
    role_code: Optional[str] = None
    role_name: Optional[str] = None
    assigned_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None


# ─── Approval Flow ────────────────────────────────────────────────

class ApprovalStep(BaseModel):
    step: int
    approver_role: str   # role code that can approve at this step
    auto_escalate_min: Optional[int] = None  # auto-escalate after N minutes


class ApprovalFlowCreate(BaseModel):
    name: str
    module: str
    trigger_event: str
    description: Optional[str] = None
    steps: list[ApprovalStep]


class ApprovalFlowResponse(BaseModel):
    id: str
    name: str
    module: str
    trigger_event: str
    description: Optional[str] = None
    steps: list[dict]
    status: str
    created_at: Optional[datetime] = None


# ─── Approval Request & Record ────────────────────────────────────

class ApprovalRequestResponse(BaseModel):
    id: str
    flow_name: Optional[str] = None
    request_type: str
    request_ref_no: Optional[str] = None
    requester_name: Optional[str] = None
    current_step: int
    status: str
    notes: Optional[str] = None
    created_at: Optional[datetime] = None


class ApprovalAction(BaseModel):
    action: str  # approved, rejected
    comment: Optional[str] = None


class ApprovalRecordResponse(BaseModel):
    id: str
    step: int
    approver_name: Optional[str] = None
    action: str
    comment: Optional[str] = None
    created_at: Optional[datetime] = None
