"""add MRP tables (mrp_masters, mrp_items)

Revision ID: 003
Revises: 002
Create Date: 2026-05-13
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # MRP Masters
    op.create_table(
        "mrp_masters",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("mps_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("mps_masters.id"), nullable=False, index=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("created_by", sa.String(100), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # MRP Items
    op.create_table(
        "mrp_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("mrp_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("mrp_masters.id"), nullable=False),
        # 物料識別
        sa.Column("product_no", sa.String(50), nullable=False, index=True),
        sa.Column("part_no", sa.String(50), nullable=False, index=True),
        sa.Column("part_name", sa.String(200), nullable=True),
        # BOM 階層
        sa.Column("bom_level", sa.Integer(), nullable=False, server_default="0"),
        # 時段 (週)
        sa.Column("period_week", sa.Integer(), nullable=False, server_default="0"),
        # MRP 運算結果
        sa.Column("gross_requirement", sa.Float(), nullable=False, server_default="0"),
        sa.Column("scheduled_receipts", sa.Float(), nullable=False, server_default="0"),
        sa.Column("projected_balance", sa.Float(), nullable=False, server_default="0"),
        sa.Column("net_requirement", sa.Float(), nullable=False, server_default="0"),
        sa.Column("planned_order_qty", sa.Float(), nullable=False, server_default="0"),
        sa.Column("planned_order_release", sa.Float(), nullable=False, server_default="0"),
        # 訂單屬性
        sa.Column("order_type", sa.String(20), nullable=False, server_default="make"),
        sa.Column("lead_time_days", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("source", sa.String(200), nullable=True),
        sa.Column("exception_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("mrp_items")
    op.drop_table("mrp_masters")
