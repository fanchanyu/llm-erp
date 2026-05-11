"""Organization models — departments, employees, users, roles, permissions, approvals."""

import uuid
from datetime import datetime, date
from sqlalchemy import (
    Column, String, Float, Integer, DateTime, Date, Boolean, Text,
    ForeignKey, Enum as SAEnum, Uuid, JSON,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


# ─── Department (組織樹) ──────────────────────────────────────────

class Department(Base):
    """Multi-level organization tree: Company → Plant → Division → Dept → Section."""
    __tablename__ = "departments"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    code = Column(String(20), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=False)
    parent_id = Column(Uuid, ForeignKey("departments.id"), nullable=True)
    manager_id = Column(Uuid, ForeignKey("employees.id"), nullable=True)
    level = Column(Integer, default=1)          # 1=Company, 2=Plant, 3=Division, ...
    sort_order = Column(Integer, default=0)
    status = Column(String(20), default="active")  # active, inactive
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    parent = relationship("Department", remote_side=[id], backref="children", foreign_keys=[parent_id])


# ─── Employee (員工) ──────────────────────────────────────────────

class Employee(Base):
    """Employee master — 1:1 with User account."""
    __tablename__ = "employees"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    employee_no = Column(String(20), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(200), nullable=True)
    phone = Column(String(50), nullable=True)
    title = Column(String(100), nullable=True)
    department_id = Column(Uuid, ForeignKey("departments.id"), nullable=False)
    manager_id = Column(Uuid, ForeignKey("employees.id"), nullable=True)
    hire_date = Column(Date, nullable=True)
    status = Column(String(20), default="active")  # active, inactive, resigned
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    department = relationship("Department", foreign_keys=[department_id])
    manager = relationship("Employee", remote_side=[id], backref="subordinates", foreign_keys=[manager_id])


# ─── User (登入帳號) ─────────────────────────────────────────────

class User(Base):
    """Login account — 1:1 with Employee."""
    __tablename__ = "users"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    employee_id = Column(Uuid, ForeignKey("employees.id"), unique=True, nullable=False)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    last_login = Column(DateTime, nullable=True)
    login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime, nullable=True)
    status = Column(String(20), default="active")  # active, locked, disabled
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    employee = relationship("Employee", foreign_keys=[employee_id])


# ─── Role (角色定義) ─────────────────────────────────────────────

class Role(Base):
    """System role definition — operator, section chief, manager, plant manager, etc."""
    __tablename__ = "roles"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    code = Column(String(50), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    level = Column(Integer, default=1)  # higher = more authority
    created_at = Column(DateTime, default=datetime.utcnow)


# ─── Role Permission (角色權限) ──────────────────────────────────

class RolePermission(Base):
    """Granular permissions per role per module."""
    __tablename__ = "role_permissions"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    role_id = Column(Uuid, ForeignKey("roles.id"), nullable=False)
    module = Column(String(50), nullable=False, index=True)   # e.g. inventory, purchase, quality
    action = Column(String(20), nullable=False)               # create, read, update, delete, approve
    scope = Column(String(20), default="department")           # all, department, self
    created_at = Column(DateTime, default=datetime.utcnow)

    role = relationship("Role", foreign_keys=[role_id])


# ─── Employee-Role Assignment (員工角色指派) ────────────────────

class EmployeeRole(Base):
    """Many-to-many: employee ↔ role."""
    __tablename__ = "employee_roles"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    employee_id = Column(Uuid, ForeignKey("employees.id"), nullable=False)
    role_id = Column(Uuid, ForeignKey("roles.id"), nullable=False)
    assigned_by = Column(Uuid, ForeignKey("employees.id"), nullable=True)
    assigned_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)

    employee = relationship("Employee", foreign_keys=[employee_id])
    role = relationship("Role", foreign_keys=[role_id])
    assigner = relationship("Employee", foreign_keys=[assigned_by])


# ─── Approval Flow Definition (簽核流程定義) ─────────────────────

class ApprovalFlow(Base):
    """Define approval workflows: who approves what in which order."""
    __tablename__ = "approval_flows"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False)
    module = Column(String(50), nullable=False, index=True)     # purchase, quality, etc.
    trigger_event = Column(String(100), nullable=False)          # purchase_order_created, etc.
    description = Column(Text, nullable=True)
    steps = Column(JSON, nullable=False)  # [{"step":1,"approver_role":"manager","auto_escalate_min":60}, ...]
    status = Column(String(20), default="active")  # active, inactive
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ─── Approval Request (簽核請求) ─────────────────────────────────

class ApprovalRequest(Base):
    """A pending approval request for a specific document/decision."""
    __tablename__ = "approval_requests"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    flow_id = Column(Uuid, ForeignKey("approval_flows.id"), nullable=False)
    request_type = Column(String(50), nullable=False)   # purchase_order, quotation, etc.
    request_ref_id = Column(Uuid, nullable=False)        # UUID of the target document
    request_ref_no = Column(String(100), nullable=True)  # human-readable reference (PO-2026-0001)
    requester_id = Column(Uuid, ForeignKey("employees.id"), nullable=False)
    current_step = Column(Integer, default=1)
    status = Column(String(20), default="pending")       # pending, approved, rejected, cancelled
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    flow = relationship("ApprovalFlow", foreign_keys=[flow_id])
    requester = relationship("Employee", foreign_keys=[requester_id])


# ─── Approval Record (簽核紀錄) ──────────────────────────────────

class ApprovalRecord(Base):
    """Each step's approval/rejection action."""
    __tablename__ = "approval_records"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    request_id = Column(Uuid, ForeignKey("approval_requests.id"), nullable=False)
    step = Column(Integer, nullable=False)
    approver_id = Column(Uuid, ForeignKey("employees.id"), nullable=False)
    action = Column(String(20), nullable=False)           # pending, approved, rejected, escalated
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    request = relationship("ApprovalRequest", foreign_keys=[request_id])
    approver = relationship("Employee", foreign_keys=[approver_id])
