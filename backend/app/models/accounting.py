"""
Accounting / Finance Models

Core entities:
- Account: 會計科目 (chart of accounts)
- JournalEntry: 傳票/分錄
- JournalLine: 傳票明細 (debit/credit lines)
- AccountsReceivable: 應收帳款
- MonthEndClose: 月結記錄
"""

import uuid
from datetime import datetime, date
from sqlalchemy import (
    Column, String, Float, Date, DateTime, Text, Boolean, ForeignKey, Uuid,
)
from sqlalchemy.orm import relationship
from app.models.inventory import Base


class Account(Base):
    __tablename__ = "accounts"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    account_no = Column(String(20), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=False)
    type = Column(String(20), nullable=False)  # asset / liability / equity / revenue / expense
    normal_balance = Column(String(4), nullable=False)  # debit / credit
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    journal_lines = relationship("JournalLine", back_populates="account")


class JournalEntry(Base):
    __tablename__ = "journal_entries"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    entry_no = Column(String(50), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=False)
    entry_date = Column(Date, nullable=False)
    period = Column(String(7), nullable=False, index=True)  # e.g. '2026-05'
    source_type = Column(String(50), nullable=True)  # PO / INV / WO / etc.
    source_id = Column(String(100), nullable=True)
    created_by = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    posted = Column(Boolean, default=False)

    lines = relationship("JournalLine", back_populates="entry",
                         cascade="all, delete-orphan")


class JournalLine(Base):
    __tablename__ = "journal_lines"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    entry_id = Column(Uuid, ForeignKey("journal_entries.id"), nullable=False)
    account_id = Column(Uuid, ForeignKey("accounts.id"), nullable=False)
    debit = Column(Float, default=0)
    credit = Column(Float, default=0)
    description = Column(Text, nullable=True)

    entry = relationship("JournalEntry", back_populates="lines")
    account = relationship("Account", back_populates="journal_lines")


class AccountsReceivable(Base):
    __tablename__ = "accounts_receivable"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    customer_name = Column(String(200), nullable=False, index=True)
    invoice_no = Column(String(50), nullable=False)
    amount = Column(Float, nullable=False)
    due_date = Column(Date, nullable=False)
    paid_amount = Column(Float, default=0)
    status = Column(String(20), default="open")  # open / overdue / paid
    created_at = Column(DateTime, default=datetime.utcnow)


class MonthEndClose(Base):
    __tablename__ = "month_end_closes"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    period = Column(String(7), unique=True, nullable=False, index=True)
    closed_at = Column(DateTime, nullable=True)
    closed_by = Column(String(100), nullable=True)
    is_closed = Column(Boolean, default=False)
