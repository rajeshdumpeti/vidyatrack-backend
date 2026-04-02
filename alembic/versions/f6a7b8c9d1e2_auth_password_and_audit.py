"""auth: password login, refresh tokens, audit logs

Revision ID: f6a7b8c9d1e2
Revises: e5f6a7b8c9d0
Create Date: 2026-03-31 00:00:00.000000

Why:
  Adds password-based login alongside existing OTP login.
  Introduces account lockout, refresh tokens, audit logs, and
  OTP purpose tracking (login / password_reset / login_2fa).
"""

from alembic import op
import sqlalchemy as sa

revision = "f6a7b8c9d1e2"
down_revision = "e5f6a7b8c9d0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add password/lockout/profile columns to users
    op.add_column("users", sa.Column("full_name", sa.String(255), nullable=True))
    op.add_column("users", sa.Column("avatar_url", sa.String(512), nullable=True))
    op.add_column("users", sa.Column("password_hash", sa.String(255), nullable=True))
    op.add_column("users", sa.Column(
        "failed_login_attempts", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("users", sa.Column(
        "locked_until", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column(
        "is_first_login", sa.Boolean(), nullable=False, server_default="true"))
    op.add_column("users", sa.Column(
        "last_login_at", sa.DateTime(timezone=True), nullable=True))

    # 2. Add purpose column to otp_requests (default "login" for all existing rows)
    op.add_column("otp_requests", sa.Column(
        "purpose", sa.String(32), nullable=False, server_default="login"))

    # 3. Create refresh_tokens table
    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(),
                  sa.ForeignKey("users.id", ondelete="CASCADE"),
                  nullable=False, index=True),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_refresh_tokens_token_hash", "refresh_tokens", ["token_hash"])

    # 4. Create audit_logs table
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(),
                  sa.ForeignKey("users.id", ondelete="SET NULL"),
                  nullable=True, index=True),
        sa.Column("event", sa.String(64), nullable=False),
        sa.Column("identifier", sa.String(255), nullable=True),
        sa.Column("ip_address", sa.String(64), nullable=True),
        sa.Column("device_type", sa.String(16), nullable=True),
        sa.Column("browser", sa.String(128), nullable=True),
        sa.Column("user_agent", sa.String(512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_audit_logs_event", "audit_logs", ["event"])


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("refresh_tokens")
    op.drop_column("otp_requests", "purpose")
    op.drop_column("users", "last_login_at")
    op.drop_column("users", "is_first_login")
    op.drop_column("users", "locked_until")
    op.drop_column("users", "failed_login_attempts")
    op.drop_column("users", "password_hash")
    op.drop_column("users", "avatar_url")
    op.drop_column("users", "full_name")
