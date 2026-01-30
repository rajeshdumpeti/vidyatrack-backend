"""restore student_notes table after accidental drop

Revision ID: e3c9b8a8a1f4
Revises: dab635796bdb
Create Date: 2026-01-30 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e3c9b8a8a1f4"
down_revision: Union[str, None] = "dab635796bdb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS student_notes (
            id SERIAL PRIMARY KEY,
            school_id INTEGER NOT NULL REFERENCES schools(id) ON DELETE CASCADE,
            student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
            author_user_id INTEGER NULL REFERENCES users(id) ON DELETE SET NULL,
            note_text TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_student_notes_school_student
            ON student_notes (school_id, student_id);
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS student_notes CASCADE;")
