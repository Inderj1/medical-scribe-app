"""add speaker diarization fields

Revision ID: add_speaker_diarization
Revises: 
Create Date: 2025-07-30

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_speaker_diarization'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add speaker-related columns to transcriptions table
    op.add_column('transcriptions', sa.Column('speaker_segments', postgresql.JSONB(), nullable=True))
    op.add_column('transcriptions', sa.Column('speaker_count', sa.Integer(), nullable=True, server_default='1'))
    op.add_column('transcriptions', sa.Column('diarization_metadata', postgresql.JSONB(), nullable=True))
    
    # Create speaker_profiles table
    op.create_table('speaker_profiles',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('session_id', sa.String(), nullable=False),
        sa.Column('speaker_label', sa.String(), nullable=False),
        sa.Column('voice_embedding', postgresql.JSONB(), nullable=True),
        sa.Column('assigned_role', sa.String(), nullable=True),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=True, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_speaker_profiles_session_id'), 'speaker_profiles', ['session_id'], unique=False)


def downgrade() -> None:
    # Drop speaker_profiles table
    op.drop_index(op.f('ix_speaker_profiles_session_id'), table_name='speaker_profiles')
    op.drop_table('speaker_profiles')
    
    # Remove speaker-related columns from transcriptions table
    op.drop_column('transcriptions', 'diarization_metadata')
    op.drop_column('transcriptions', 'speaker_count')
    op.drop_column('transcriptions', 'speaker_segments')