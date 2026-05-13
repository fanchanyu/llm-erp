"""add MPS tables (mps_masters, mps_entries, time_fences)

Revision ID: 002
Revises: 001
Create Date: 2026-05-13
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # MPS Masters
    op.create_table(
        "mps_masters",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("start_week", sa.Integer(), nullable=False),
        sa.Column("end_week", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("lot_sizing_rule", sa.String(20), nullable=False, server_default="lot_for_lot"),
        sa.Column("fixed_lot_qty", sa.Float(), nullable=True),
        sa.Column("safety_stock", sa.Float(), nullable=False, server_default="0"),
        sa.Column("created_by", sa.String(100), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # MPS Entries
    op.create_table(
        "mps_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("mps_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("mps_masters.id"), nullable=False),
        sa.Column("product_no", sa.String(50), nullable=False, index=True),
        sa.Column("product_name", sa.String(200), nullable=True),
        sa.Column("period_week", sa.Integer(), nullable=False),
        sa.Column("week_number", sa.Integer(), nullable=True),
        sa.Column("forecast_qty", sa.Float(), nullable=False, server_default="0"),
        sa.Column("customer_orders_qty", sa.Float(), nullable=False, server_default="0"),
        sa.Column("gross_requirement", sa.Float(), nullable=False, server_default="0"),
        sa.Column("scheduled_receipts", sa.Float(), nullable=False, server_default="0"),
        sa.Column("projected_balance", sa.Float(), nullable=False, server_default="0"),
        sa.Column("planned_order_qty", sa.Float(), nullable=False, server_default="0"),
        sa.Column("planned_order_release", sa.Float(), nullable=True),
        sa.Column("available_to_promise", sa.Float(), nullable=False, server_default="0"),
        sa.Column("time_fence_type", sa.String(20), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="planned"),
        sa.Column("exception_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # Time Fences
    op.create_table(
        "time_fences",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("mps_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("mps_masters.id"), nullable=False),
        sa.Column("fence_type", sa.String(20), nullable=False),
        sa.Column("fence_week", sa.Integer(), nullable=False),
        sa.Column("description", sa.String(200), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("time_fences")
    op.drop_table("mps_entries")
    op.drop_table("mps_masters")
