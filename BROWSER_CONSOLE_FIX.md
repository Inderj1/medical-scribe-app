# Browser Console Fix

Since the Stop button is not visible in the UI, you can end the recording session manually using the browser console.

## Steps:

1. **Open Browser Developer Console**
   - Chrome/Edge: Press `Cmd+Option+J` (Mac) or `Ctrl+Shift+J` (Windows)
   - Firefox: Press `Cmd+Option+K` (Mac) or `Ctrl+Shift+K` (Windows)
   - Safari: Enable Developer menu first, then `Cmd+Option+C`

2. **Paste this code in the console:**

```javascript
// End the current streaming session
async function endSession() {
  const sessionId = 'fb218c58-998e-44eb-92a1-c45ff2fe542f';
  const token = await window.Clerk.session.getToken();
  
  const response = await fetch(`http://localhost:8000/api/v1/streaming/${sessionId}/end`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    }
  });
  
  if (response.ok) {
    console.log('Session ended successfully! Sections will update in 5-10 seconds...');
  } else {
    console.error('Failed to end session:', response.status);
  }
}

endSession();
```

3. **Press Enter to run the code**

4. **Wait 5-10 seconds** for the AI to process your transcript

5. **Watch the sections populate** with the medical information extracted from your conversation

## What will happen:
- The backend will process all 211 words of your medical conversation
- The AI will extract information about:
  - Chief complaint (chest pain symptoms)
  - Family history (no heart disease)
  - Planned diagnostics (ECG)
  - Lifestyle recommendations
  - Treatment discussion
- Each section will update with the relevant information