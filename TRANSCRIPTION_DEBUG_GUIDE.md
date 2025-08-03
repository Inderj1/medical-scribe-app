# Transcription Debug Guide

## How to Test Transcription on Clinical Notes Page

### 1. Prerequisites
- Backend API v2 running on http://localhost:8000
- Frontend running on http://localhost:3100
- PostgreSQL and Redis running (via Docker)

### 2. Testing Audio Upload

1. Navigate to http://localhost:3100/clinical-notes
2. Select a patient from the patient records page first
3. In the left panel (Transcription), you'll see:
   - Voice recording button (for live recording)
   - Audio upload section at the bottom

### 3. Upload Process

1. Click "Upload Audio Files" button
2. Select an audio file (MP3, WAV, M4A, etc.)
3. The file will be uploaded and processed through the v2 agents pipeline:
   - TranscriptionAgent → ClinicalAnalysisAgent → NoteStructuringAgent → QAAgent

### 4. Monitor Progress

Check the browser console for:
- Upload progress
- SSE (Server-Sent Events) updates
- Section completion notifications

Check the backend logs for:
- Agent processing stages
- Any errors in the pipeline

### 5. Content Distribution

The transcribed content is distributed to sections based on the agent analysis:
- **Chief Complaint**: Main reason for visit
- **History of Present Illness**: Details about current condition
- **Past Medical History**: Previous conditions
- **Medications**: Current medications
- **Allergies**: Known allergies
- **Physical Examination**: Exam findings
- **Assessment**: Clinical assessment
- **Plan**: Treatment plan

### 6. Common Issues & Solutions

#### Issue: Upload fails with 401/403
**Solution**: Mock auth is being used. Check browser console for auth token.

#### Issue: No sections appear after upload
**Solution**: 
1. Check backend logs for agent errors
2. Verify OpenAI API key is set in backend .env
3. Check SSE connection in browser Network tab

#### Issue: SSE connection fails
**Solution**: 
1. Ensure CORS is properly configured
2. Check that frontend is using correct API URL

### 7. Test Audio Files

You can create a test audio file using macOS:
```bash
# Record a 30-second test audio
say -o test_medical.aiff "The patient is a 45-year-old male presenting with chest pain that started 2 hours ago. The pain is described as sharp and radiates to the left arm. Patient has a history of hypertension and is currently taking lisinopril 10mg daily. No known drug allergies. Vital signs show blood pressure 150 over 90. Physical examination reveals mild tenderness in the chest area. Assessment indicates possible angina. Plan includes ECG, cardiac enzymes, and cardiology consultation."

# Convert to MP3
ffmpeg -i test_medical.aiff test_medical.mp3
```

### 8. Backend API Endpoints

- **Upload**: POST `/api/v1/transcription/upload`
- **Status**: GET `/api/v1/transcription/{id}/status`
- **Results**: GET `/api/v1/transcription/{id}`
- **SSE**: GET `/api/v1/sse/subscribe?channel=transcription_{id}`

### 9. Debugging Tips

1. **Enable debug mode in frontend**:
   - The debug panel shows available sections and SSE status
   - Located at the top of the Clinical Notes panel

2. **Check agent logs**:
   ```bash
   # In backend terminal
   grep "agent" v2_backend.log
   ```

3. **Monitor SSE events**:
   - Open browser DevTools → Network tab
   - Filter by "sse" to see event stream
   - Check for section_completed events

4. **Verify database**:
   ```bash
   docker-compose exec postgres psql -U medscribe -d medical_scribe_db
   \dt  # List tables
   SELECT * FROM transcriptions ORDER BY created_at DESC LIMIT 5;
   SELECT * FROM clinical_notes ORDER BY created_at DESC LIMIT 5;
   ```

### 10. Expected Flow

1. Audio upload → Transcription record created
2. Background task starts agent workflow
3. SSE publishes progress updates
4. Sections are populated as agents complete
5. Final QA report generated
6. Complete clinical note available

The entire process typically takes 30-60 seconds depending on audio length.