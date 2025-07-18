# Epic Integration Guide - AI-ProfixMed-HealthCare

## Quick Start

Your Epic app is configured and ready to integrate. Follow these steps to connect it to the Medical Scribe application.

## 1. Configure Backend

### Update `.env` file in `/backend`:

```env
# Epic Configuration (Your App Details)
EPIC_CLIENT_ID=0eb42959-ba12-4e23-81c9-0a523d40fd4a  # Non-production
EPIC_CLIENT_SECRET=your_sandbox_client_secret_here
EPIC_BASE_URL=https://fhir.epic.com/interconnect-fhir-oauth
EPIC_USE_SANDBOX=true
```

### Get your Client Secret:
1. Go to https://fhir.epic.com/Developer/Apps
2. Find your app "AI-ProfixMed-HealthCare"
3. Copy the Sandbox Client Secret
4. Add it to your `.env` file

## 2. Configure Frontend

### Update `.env` file in `/frontend`:

```env
REACT_APP_EPIC_CLIENT_ID=0eb42959-ba12-4e23-81c9-0a523d40fd4a
REACT_APP_EPIC_REDIRECT_URI=https://localhost:3000/callback
```

## 3. Setup HTTPS for localhost

Epic requires HTTPS even for localhost. Create self-signed certificates:

```bash
# In the frontend directory
mkdir certificates
cd certificates

# Generate private key
openssl genrsa -out localhost.key 2048

# Generate certificate
openssl req -new -x509 -key localhost.key -out localhost.crt -days 365 \
  -subj /CN=localhost

# Trust the certificate (macOS)
sudo security add-trusted-cert -d -r trustRoot -k /Library/Keychains/System.keychain localhost.crt
```

### Update package.json to use HTTPS:

```json
"scripts": {
  "start": "HTTPS=true SSL_CRT_FILE=certificates/localhost.crt SSL_KEY_FILE=certificates/localhost.key react-scripts start",
}
```

## 4. Test Epic Integration

### Step 1: Start the application

```bash
# Terminal 1 - Backend
cd backend
source venv/bin/activate
uvicorn app.main:app --reload

# Terminal 2 - Frontend (with HTTPS)
cd frontend
npm start
```

### Step 2: Test SMART Launch

Epic will launch your app with a URL like:
```
https://localhost:3000/launch?iss=https://fhir.epic.com/interconnect-fhir-oauth/api/FHIR/R4&launch=eyJhbGc...
```

The app will:
1. Redirect to Epic for authorization
2. Epic redirects back to `https://localhost:3000/callback`
3. Exchange code for access token
4. Import patient data

### Step 3: Test with Epic Sandbox Patients

Use these test patients:
- **Jason Argonaut** - Basic test patient
- **Derrick Lin** - Complex medical history
- **Timmy Smart** - Pediatric patient

## 5. Integration Workflow

### From Epic EHR:

1. **Clinician launches app** from Epic workspace
2. **App receives launch context** (patient, encounter)
3. **Automatic patient import** to Medical Scribe
4. **Start voice recording** for documentation
5. **AI processes audio** and creates structured notes
6. **Push notes back to Epic** (if configured)

### From Medical Scribe:

1. **Search patient** using Epic integration
2. **Import patient data** including:
   - Demographics
   - Active medications
   - Allergies
   - Problem list
   - Recent vitals
3. **Create encounter** with Epic context
4. **Document visit** with AI assistance

## 6. AI Agent Features

Your app supports these AI-powered features:

### Voice Commands:
```
"Show patient's medications"
"Add chief complaint: chest pain"
"Order CBC and metabolic panel"
"Create discharge summary"
```

### Automated Actions:
- **Summarize** patient history
- **Suggest** differential diagnoses
- **Generate** visit notes
- **Propose** treatment plans

## 7. API Examples

### Get Patient from Epic:

```bash
curl -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  "https://fhir.epic.com/interconnect-fhir-oauth/api/FHIR/R4/Patient/Tbt3KuCY0B5PSrJvCu2j-PlK.aiHsu2xUjUM8bWpetXoB"
```

### Search Conditions:

```bash
curl -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  "https://fhir.epic.com/interconnect-fhir-oauth/api/FHIR/R4/Condition?patient=Tbt3KuCY0B5PSrJvCu2j-PlK.aiHsu2xUjUM8bWpetXoB"
```

## 8. Troubleshooting

### Common Issues:

1. **"Invalid redirect URI"**
   - Ensure `https://localhost:3000/callback` is registered in Epic
   - Check HTTPS is working correctly

2. **"Client authentication failed"**
   - Verify client secret is correct
   - Check you're using the sandbox client ID

3. **"No launch context"**
   - Must launch from Epic (not direct URL)
   - Check launch parameter is passed correctly

4. **CORS errors**
   - Backend must allow `https://localhost:3000`
   - Check CORS configuration

### Debug Mode:

Enable detailed logging:

```python
# In backend/.env
DEBUG=True
LOG_LEVEL=DEBUG
```

```javascript
// In frontend
localStorage.setItem('debug', 'epic:*');
```

## 9. Production Deployment

When ready for production:

1. **Switch to Production Client ID**:
   ```env
   EPIC_CLIENT_ID=cb117f80-34b1-4bdf-a404-b69cf3d044de
   EPIC_USE_SANDBOX=false
   ```

2. **Update Redirect URI** to production domain

3. **Complete Epic Requirements**:
   - Security assessment
   - Interoperability testing
   - Customer organization approval

4. **Configure Organization-Specific Endpoints**:
   Each healthcare organization has their own Epic URL

## 10. Next Steps

1. ✅ Test patient import from Epic
2. ✅ Verify audio recording works
3. ✅ Test AI transcription and note generation
4. ⬜ Configure note push-back to Epic
5. ⬜ Add more AI agent commands
6. ⬜ Test with clinical users
7. ⬜ Prepare for App Orchard certification

## Support

- Epic Developer Support: https://fhir.epic.com/Contact
- Medical Scribe Issues: Create GitHub issue
- AI Agent Documentation: See `/docs/AI_AGENTS.md`

Remember: Your app "AI-ProfixMed-HealthCare" is already configured in Epic. You just need to add the client secret and start testing!