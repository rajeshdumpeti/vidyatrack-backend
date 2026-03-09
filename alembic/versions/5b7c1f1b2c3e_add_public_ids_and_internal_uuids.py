"""add public ids and internal uuids

Revision ID: 5b7c1f1b2c3e
Revises: 4e8114d023db
Create Date: 2026-03-05
"""

from __future__ import annotations

import re
import secrets
import time
import uuid
from datetime import datetime

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "5b7c1f1b2c3e"
down_revision = "4e8114d023db"
branch_labels = None
depends_on = None

ENTITY_CODES = {
    "school": "SCH",
    "class": "CLS",
    "section": "SEC",
    "subject": "SUB",
    "student": "STU",
    "teacher": "TCH",
    "principal": "PRN",
    "management_admin": "MGT",
}


def uuid7() -> uuid.UUID:
    ms = int(time.time() * 1000)
    time_high = ms & ((1 << 48) - 1)
    rand_a = secrets.randbits(12)
    rand_b = secrets.randbits(62)
    version = 0x7
    variant = 0b10
    uuid_int = (
        (time_high << 80)
        | (version << 76)
        | (rand_a << 64)
        | (variant << 62)
        | rand_b
    )
    return uuid.UUID(int=uuid_int)


def normalize_tenant_code(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]+", "", (value or "").strip().upper())
    return cleaned[:6] if cleaned else "SCH"


def derive_tenant_code(name: str) -> str:
    tokens = re.findall(r"[A-Za-z0-9]+", (name or "").upper())
    if not tokens:
        return "SCH"
    if len(tokens) == 1:
        base = tokens[0][:6]
    else:
        base = "".join(token[0] for token in tokens)[:6]
    if len(base) < 3:
        base = (tokens[0][:6]).ljust(3, "X")
    return base


def ensure_unique_tenant_code(existing: set[str], base: str) -> str:
    base = normalize_tenant_code(base)
    candidate = base
    suffix = 1
    while candidate in existing:
        suffix_str = str(suffix)
        trim = max(0, 6 - len(suffix_str))
        candidate = f"{base[:trim]}{suffix_str}"
        suffix += 1
    existing.add(candidate)
    return candidate


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = set(inspector.get_table_names())

    op.create_table(
        "public_id_counters",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_code", sa.String(length=16), nullable=False),
        sa.Column("entity", sa.String(length=32), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("next_seq", sa.Integer(), nullable=False, server_default="1"),
        sa.UniqueConstraint("tenant_code", "entity", "year", name="uq_public_id_counter"),
    )
    op.create_index("ix_public_id_counters_tenant_code", "public_id_counters", ["tenant_code"], unique=False)
    op.create_index("ix_public_id_counters_entity", "public_id_counters", ["entity"], unique=False)

    uuid_col = postgresql.UUID(as_uuid=True)

    tables = [
        "schools",
        "classes",
        "sections",
        "subjects",
        "students",
        "teachers",
        "principals",
        "management_admins",
    ]

    principals_created = False
    if "principals" not in existing_tables:
        op.create_table(
            "principals",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("internal_id", uuid_col, nullable=False),
            sa.Column("public_id", sa.String(length=32), nullable=False),
            sa.Column("school_id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(length=200), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(["school_id"], ["schools.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
            sa.UniqueConstraint("school_id", name="uq_principals_school_id"),
            sa.UniqueConstraint("user_id", name="uq_principals_user_id"),
        )
        op.create_index("ix_principals_internal_id", "principals", ["internal_id"], unique=True)
        op.create_index("ix_principals_public_id", "principals", ["public_id"], unique=True)
        op.create_index(op.f("ix_principals_school_id"), "principals", ["school_id"], unique=False)
        op.create_index(op.f("ix_principals_user_id"), "principals", ["user_id"], unique=False)
        existing_tables.add("principals")
        principals_created = True

    for table in tables:
        if table not in existing_tables:
            continue
        if table == "principals" and principals_created:
            continue
        op.add_column(table, sa.Column("internal_id", uuid_col, nullable=True))
        op.add_column(table, sa.Column("public_id", sa.String(length=32), nullable=True))
        op.create_index(f"ix_{table}_public_id", table, ["public_id"], unique=True)
        op.create_index(f"ix_{table}_internal_id", table, ["internal_id"], unique=True)
    now_year = datetime.utcnow().year

    schools = sa.table(
        "schools",
        sa.column("id", sa.Integer),
        sa.column("name", sa.String),
        sa.column("code", sa.String),
        sa.column("internal_id", uuid_col),
        sa.column("public_id", sa.String),
    )
    classes = sa.table(
        "classes",
        sa.column("id", sa.Integer),
        sa.column("school_id", sa.Integer),
        sa.column("internal_id", uuid_col),
        sa.column("public_id", sa.String),
    )
    sections = sa.table(
        "sections",
        sa.column("id", sa.Integer),
        sa.column("school_id", sa.Integer),
        sa.column("internal_id", uuid_col),
        sa.column("public_id", sa.String),
    )
    subjects = sa.table(
        "subjects",
        sa.column("id", sa.Integer),
        sa.column("school_id", sa.Integer),
        sa.column("internal_id", uuid_col),
        sa.column("public_id", sa.String),
    )
    teachers = sa.table(
        "teachers",
        sa.column("id", sa.Integer),
        sa.column("school_id", sa.Integer),
        sa.column("internal_id", uuid_col),
        sa.column("public_id", sa.String),
    )
    principals = sa.table(
        "principals",
        sa.column("id", sa.Integer),
        sa.column("school_id", sa.Integer),
        sa.column("internal_id", uuid_col),
        sa.column("public_id", sa.String),
    )
    management_admins = sa.table(
        "management_admins",
        sa.column("id", sa.Integer),
        sa.column("school_id", sa.Integer),
        sa.column("internal_id", uuid_col),
        sa.column("public_id", sa.String),
    )
    students = sa.table(
        "students",
        sa.column("id", sa.Integer),
        sa.column("school_id", sa.Integer),
        sa.column("admission_date", sa.Date),
        sa.column("internal_id", uuid_col),
        sa.column("public_id", sa.String),
    )
    public_id_counters = sa.table(
        "public_id_counters",
        sa.column("id", uuid_col),
        sa.column("tenant_code", sa.String),
        sa.column("entity", sa.String),
        sa.column("year", sa.Integer),
        sa.column("next_seq", sa.Integer),
    )

    school_rows = conn.execute(sa.select(schools.c.id, schools.c.name, schools.c.code)).fetchall()
    existing_codes = {row.code for row in school_rows if row.code}
    tenant_by_school: dict[int, str] = {}

    for row in school_rows:
        if row.code:
            tenant_code = normalize_tenant_code(row.code)
        else:
            tenant_code = ensure_unique_tenant_code(existing_codes, derive_tenant_code(row.name))
            conn.execute(
                schools.update().where(schools.c.id == row.id).values(code=tenant_code)
            )
        tenant_by_school[row.id] = tenant_code

        school_public_id = f"{tenant_code}-{ENTITY_CODES['school']}-{now_year}-000001"
        conn.execute(
            schools.update()
            .where(schools.c.id == row.id)
            .values(internal_id=uuid7(), public_id=school_public_id)
        )

        conn.execute(
            public_id_counters.insert().values(
                id=uuid7(),
                tenant_code=tenant_code,
                entity="school",
                year=0,
                next_seq=2,
            )
        )

    def assign_public_ids(
        table: sa.Table,
        entity: str,
        *,
        year_resolver=None,
    ) -> None:
        cols = [table.c.id, table.c.school_id]
        if "admission_date" in table.c:
            cols.append(table.c.admission_date)
        rows = conn.execute(sa.select(*cols)).fetchall()

        seq_by_key: dict[tuple[int, int], int] = {}

        for row in rows:
            display_year = now_year
            if year_resolver:
                display_year = year_resolver(row) or now_year
            key_year = display_year if entity == "student" else 0
            key = (row.school_id, key_year)
            seq = seq_by_key.get(key, 0) + 1
            seq_by_key[key] = seq

            tenant_code = tenant_by_school[row.school_id]
            entity_code = ENTITY_CODES[entity]
            public_id = f"{tenant_code}-{entity_code}-{display_year}-{seq:06d}"

            conn.execute(
                table.update()
                .where(table.c.id == row.id)
                .values(internal_id=uuid7(), public_id=public_id)
            )

        for (school_id, counter_year), max_seq in seq_by_key.items():
            tenant_code = tenant_by_school[school_id]
            conn.execute(
                public_id_counters.insert().values(
                    id=uuid7(),
                    tenant_code=tenant_code,
                    entity=entity,
                    year=counter_year,
                    next_seq=max_seq + 1,
                )
            )

    assign_public_ids(classes, "class")
    assign_public_ids(sections, "section")
    assign_public_ids(subjects, "subject")
    assign_public_ids(teachers, "teacher")
    assign_public_ids(principals, "principal")
    assign_public_ids(management_admins, "management_admin")

    def student_year_resolver(row) -> int | None:
        if row.admission_date:
            return row.admission_date.year
        return now_year

    assign_public_ids(students, "student", year_resolver=student_year_resolver)

    for table in tables:
        op.alter_column(table, "internal_id", nullable=False)
        op.alter_column(table, "public_id", nullable=False)


def downgrade() -> None:
    tables = [
        "management_admins",
        "principals",
        "teachers",
        "students",
        "subjects",
        "sections",
        "classes",
        "schools",
    ]

    for table in tables:
        op.drop_index(f"ix_{table}_internal_id", table_name=table)
        op.drop_index(f"ix_{table}_public_id", table_name=table)
        op.drop_column(table, "public_id")
        op.drop_column(table, "internal_id")

    op.drop_index("ix_public_id_counters_entity", table_name="public_id_counters")
    op.drop_index("ix_public_id_counters_tenant_code", table_name="public_id_counters")
    op.drop_table("public_id_counters")
