"""restore student_notes table if missing

Revision ID: c4b1f0a1b2cd
Revises: b81809ab7aaf
Create Date: 2026-01-13 12:10:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "c4b1f0a1b2cd"
down_revision: Union[str, None] = "b81809ab7aaf"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name = 'student_notes'
            ) THEN
                CREATE TABLE student_notes (
                    id SERIAL PRIMARY KEY,
                    school_id INTEGER NOT NULL
                        REFERENCES schools(id) ON DELETE CASCADE,
                    student_id INTEGER NOT NULL
                        REFERENCES students(id) ON DELETE CASCADE,
                    author_user_id INTEGER NULL
                        REFERENCES users(id) ON DELETE SET NULL,
                    note_text TEXT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
                );

                CREATE INDEX IF NOT EXISTS ix_student_notes_school_student
                    ON student_notes (school_id, student_id);
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP TABLE IF EXISTS student_notes CASCADE;
        """
    )
