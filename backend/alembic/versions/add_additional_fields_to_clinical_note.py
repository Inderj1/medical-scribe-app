"""Add additional_notes and care_coordination to clinical_notes

Revision ID: add_additional_fields
Revises: add_missing_patient_columns
Create Date: 2025-01-30 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_additional_fields'
down_revision = 'add_missing_patient_columns'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new columns to clinical_notes table
    op.add_column('clinical_notes', sa.Column('additional_notes', sa.Text(), nullable=True))
    op.add_column('clinical_notes', sa.Column('care_coordination', sa.Text(), nullable=True))


def downgrade() -> None:
    # Remove columns in downgrade
    op.drop_column('clinical_notes', 'care_coordination')
    op.drop_column('clinical_notes', 'additional_notes')