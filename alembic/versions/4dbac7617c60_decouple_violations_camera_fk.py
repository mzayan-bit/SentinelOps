"""decouple_violations_camera_fk

Revision ID: 4dbac7617c60
Revises: faf126954239
Create Date: 2026-06-26 21:13:31.679612

Changes violations.camera_id from a UUID FK to cameras.id into a plain
VARCHAR(128) column with no foreign key constraint.  This allows the
existing AlertService (which uses arbitrary string camera IDs like
"cam01") to persist violations without requiring a registered camera row.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4dbac7617c60'
down_revision: Union[str, Sequence[str], None] = 'faf126954239'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Remove FK constraint from violations.camera_id.

    On PostgreSQL the column type changes from UUID to VARCHAR(128).
    On SQLite the FK was already soft-enforced so this is a no-op for
    the local dev database.
    """
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.drop_constraint(
            "violations_camera_id_fkey", "violations", type_="foreignkey"
        )
        op.alter_column(
            "violations",
            "camera_id",
            existing_type=sa.UUID(),
            type_=sa.String(length=128),
            existing_nullable=False,
        )


def downgrade() -> None:
    """Restore FK constraint on violations.camera_id."""
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.alter_column(
            "violations",
            "camera_id",
            existing_type=sa.String(length=128),
            type_=sa.UUID(),
            existing_nullable=False,
        )
        op.create_foreign_key(
            "violations_camera_id_fkey",
            "violations",
            "cameras",
            ["camera_id"],
            ["id"],
        )
