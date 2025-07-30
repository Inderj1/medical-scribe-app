"""add missing patient columns

Revision ID: add_missing_columns
Revises: 
Create Date: 2025-07-29 22:15:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_missing_columns'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Add missing columns if they don't exist
    try:
        op.add_column('patients', sa.Column('insurance_info', postgresql.JSONB(), nullable=True))
    except:
        pass  # Column already exists
    
    try:
        op.add_column('patients', sa.Column('emergency_contact', postgresql.JSONB(), nullable=True))
    except:
        pass  # Column already exists
    
    # Also add missing encounter column
    try:
        op.add_column('encounters', sa.Column('ehr_encounter_id', sa.String(), nullable=True))
    except:
        pass  # Column already exists


def downgrade():
    # Remove columns
    op.drop_column('patients', 'insurance_info')
    op.drop_column('patients', 'emergency_contact')
    op.drop_column('encounters', 'ehr_encounter_id')