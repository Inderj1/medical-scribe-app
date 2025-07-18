#!/bin/bash
# Script to revert transcription UI changes

echo "Reverting Clinical Notes transcription changes..."

# Remove new files
rm -f src/components/ClinicalNotes/LiveTranscription.tsx

# Restore backup files
if [ -f src/pages/ClinicalNotesPage.backup.tsx ]; then
    mv src/pages/ClinicalNotesPage.backup.tsx src/pages/ClinicalNotesPage.tsx
    echo "✓ Restored ClinicalNotesPage.tsx"
fi

if [ -f src/components/ClinicalNotes/PatientSummaryVitals.backup.tsx ]; then
    mv src/components/ClinicalNotes/PatientSummaryVitals.backup.tsx src/components/ClinicalNotes/PatientSummaryVitals.tsx
    echo "✓ Restored PatientSummaryVitals.tsx"
fi

echo "Revert complete! Please restart the development server."