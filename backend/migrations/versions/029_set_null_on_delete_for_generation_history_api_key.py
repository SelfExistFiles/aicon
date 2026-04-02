"""set null on delete for generation history api key

Revision ID: 029
Revises: 028
Create Date: 2026-04-03 07:35:00.000000

"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "029"
down_revision = "028"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint(
        "movie_generation_history_api_key_id_fkey",
        "movie_generation_history",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "movie_generation_history_api_key_id_fkey",
        "movie_generation_history",
        "api_keys",
        ["api_key_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade():
    op.drop_constraint(
        "movie_generation_history_api_key_id_fkey",
        "movie_generation_history",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "movie_generation_history_api_key_id_fkey",
        "movie_generation_history",
        "api_keys",
        ["api_key_id"],
        ["id"],
    )
