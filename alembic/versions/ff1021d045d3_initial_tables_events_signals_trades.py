"""initial tables: events, signals, trades

Revision ID: ff1021d045d3
Revises: 
Create Date: 2026-04-08 23:58:24.509424

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ff1021d045d3'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source", sa.String(64), nullable=False),
        sa.Column("source_url", sa.Text, nullable=False, server_default=""),
        sa.Column("headline", sa.Text, nullable=False),
        sa.Column("body", sa.Text, nullable=False, server_default=""),
        sa.Column(
            "category",
            sa.Enum("CONFLICT", "ECONOMIC", "POLITICAL", "CLIMATE", "CYBER", "SOCIAL", name="categoryenum"),
            nullable=False,
        ),
        sa.Column("subcategory", sa.String(128), nullable=False, server_default=""),
        sa.Column("geo_lat", sa.Float, nullable=True),
        sa.Column("geo_lng", sa.Float, nullable=True),
        sa.Column("countries", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("entities", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("severity", sa.Float, nullable=False, server_default="0"),
        sa.Column("velocity", sa.Float, nullable=False, server_default="0"),
        sa.Column("confidence", sa.Float, nullable=False, server_default="0"),
        sa.Column(
            "urgency",
            sa.Enum("routine", "elevated", "critical", name="urgencyenum"),
            nullable=True,
        ),
        sa.Column("affected_assets", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("raw", sa.JSON, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_events_timestamp", "events", ["timestamp"])
    op.create_index("ix_events_source", "events", ["source"])
    op.create_index("ix_events_category", "events", ["category"])
    op.create_index("ix_events_severity", "events", ["severity"])
    op.create_index("ix_events_severity_timestamp", "events", ["severity", "timestamp"])
    op.create_index("ix_events_category_timestamp", "events", ["category", "timestamp"])

    op.create_table(
        "signals",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("event_id", sa.String(36), sa.ForeignKey("events.id"), nullable=False),
        sa.Column("asset", sa.String(32), nullable=False),
        sa.Column(
            "direction",
            sa.Enum("LONG", "SHORT", "NEUTRAL", name="directionenum"),
            nullable=False,
        ),
        sa.Column("magnitude", sa.Float, nullable=False),
        sa.Column("confidence", sa.Float, nullable=False),
        sa.Column("timeframe", sa.String(8), nullable=False),
        sa.Column("reasoning", sa.Text, nullable=False),
        sa.Column("correlated_assets", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("historical_precedent", sa.Text, nullable=False, server_default=""),
        sa.Column("second_order", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actual_move_pct", sa.Float, nullable=True),
        sa.Column("was_correct", sa.Boolean, nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_signals_event_id", "signals", ["event_id"])
    op.create_index("ix_signals_asset", "signals", ["asset"])
    op.create_index("ix_signals_confidence", "signals", ["confidence"])
    op.create_index("ix_signals_asset_confidence", "signals", ["asset", "confidence"])

    op.create_table(
        "trades",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("signal_id", sa.String(36), sa.ForeignKey("signals.id"), nullable=False),
        sa.Column("asset", sa.String(32), nullable=False),
        sa.Column(
            "direction",
            sa.Enum("LONG", "SHORT", "NEUTRAL", name="directionenum"),
            nullable=False,
        ),
        sa.Column("size_pct", sa.Float, nullable=False),
        sa.Column("entry_price", sa.Float, nullable=False),
        sa.Column("stop_loss", sa.Float, nullable=False),
        sa.Column("take_profit", sa.Float, nullable=False),
        sa.Column(
            "status",
            sa.Enum("PENDING", "OPEN", "CLOSED", "CANCELLED", name="tradestatusenum"),
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column("pnl", sa.Float, nullable=False, server_default="0"),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("close_reason", sa.String(64), nullable=False, server_default=""),
        sa.Column("broker_order_id", sa.String(64), nullable=True),
    )
    op.create_index("ix_trades_signal_id", "trades", ["signal_id"])
    op.create_index("ix_trades_asset", "trades", ["asset"])
    op.create_index("ix_trades_status", "trades", ["status"])


def downgrade() -> None:
    op.drop_table("trades")
    op.drop_table("signals")
    op.drop_table("events")
    op.execute("DROP TYPE IF EXISTS tradestatusenum")
    op.execute("DROP TYPE IF EXISTS directionenum")
    op.execute("DROP TYPE IF EXISTS urgencyenum")
    op.execute("DROP TYPE IF EXISTS categoryenum")
