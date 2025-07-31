# Debugging Guide: Sections Not Updating

## Current Issue
Your speech is being captured (200+ words) but sections aren't updating because:
- SSE connection shows "0 subscribers" when publishing events
- The session was ended before you started speaking

## What's Happening in Your Test

1. **22:28:35** - Started new session
2. **22:28:36** - Ended session (1 second later, empty transcript!)
3. **22:29:21** - Started speaking (but session already closed)
4. **22:30:54** - Reached 200 words, triggered analysis
5. **Problem**: SSE had 0 subscribers, so no UI updates

## The Right Way to Test

### Step 1: Refresh the Page
- This clears any old sessions
- Opens http://localhost:3100 in a new tab

### Step 2: Start Recording Properly
1. Click the microphone icon
2. **IMMEDIATELY start speaking** (don't wait)
3. Keep speaking your medical conversation
4. Only click stop AFTER you've finished speaking

### Step 3: What to Say (Example)
"Patient presents with chest pain radiating to left arm. Pain started 3 hours ago, 8 out of 10 severity. Associated with shortness of breath and diaphoresis. Patient has history of hypertension and diabetes. Currently taking metformin 500mg twice daily and lisinopril 10mg daily. No known drug allergies. Vital signs show blood pressure 160/95, heart rate 110, oxygen saturation 94%. Physical exam reveals mild distress, cardiac exam shows regular rhythm with no murmurs. Plan to order ECG, troponin levels, and chest x-ray. Consider aspirin 325mg and nitroglycerin sublingual."

### Step 4: Check Browser Console
You should see:
- `[SSE] Section completed:` events
- Sections updating in the UI

## Common Mistakes
- ❌ Clicking stop before speaking
- ❌ Waiting too long after clicking microphone
- ❌ Speaking after the session has ended
- ✅ Click mic → Speak immediately → Stop when done