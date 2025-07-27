-- Migration: Add batch transcription fields to transcriptions table
-- Date: 2025-01-27

-- Add new columns to transcriptions table
ALTER TABLE transcriptions 
ADD COLUMN IF NOT EXISTS audio_file_path TEXT,
ADD COLUMN IF NOT EXISTS transcription_text TEXT,
ADD COLUMN IF NOT EXISTS clinical_note TEXT,
ADD COLUMN IF NOT EXISTS status VARCHAR(50) DEFAULT 'pending',
ADD COLUMN IF NOT EXISTS format_preference VARCHAR(50) DEFAULT 'soap';

-- Add index on status for efficient querying
CREATE INDEX IF NOT EXISTS idx_transcriptions_status ON transcriptions(status);

-- Add index on encounter_id for joins
CREATE INDEX IF NOT EXISTS idx_transcriptions_encounter_id ON transcriptions(encounter_id);

-- Update existing records to have a status
UPDATE transcriptions 
SET status = CASE 
    WHEN is_final = true THEN 'completed'
    ELSE 'pending'
END
WHERE status IS NULL;