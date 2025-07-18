# Epic App Configuration - AI-ProfixMed-HealthCare

## Your Epic App Details

- **Application Name**: AI-ProfixMed-HealthCare
- **Production Client ID**: cb117f80-34b1-4bdf-a404-b69cf3d044de
- **Non-Production Client ID**: 0eb42959-ba12-4e23-81c9-0a523d40fd4a
- **Redirect URI**: https://localhost:3000/callback
- **App Type**: Confidential Client with Persistent Access
- **FHIR Versions**: DSTU2, STU3, R4
- **SMART Versions**: v1 and v2

## Configuration Steps

### 1. Update Backend Environment Variables

Create or update `/backend/.env`:

```env
# Epic Configuration
EPIC_CLIENT_ID_PROD=cb117f80-34b1-4bdf-a404-b69cf3d044de
EPIC_CLIENT_ID_SANDBOX=0eb42959-ba12-4e23-81c9-0a523d40fd4a
EPIC_CLIENT_SECRET=your_sandbox_client_secret_here
EPIC_BASE_URL=https://fhir.epic.com/interconnect-fhir-oauth
EPIC_REDIRECT_URI=https://localhost:3000/callback
EPIC_JWK_SET_URL_PROD=https://fhir.epic.com
EPIC_JWK_SET_URL_SANDBOX=http://fhir.epic.com
EPIC_USE_SANDBOX=true

# Set the appropriate client ID based on environment
EPIC_CLIENT_ID=${EPIC_USE_SANDBOX:+$EPIC_CLIENT_ID_SANDBOX}${EPIC_USE_SANDBOX:-$EPIC_CLIENT_ID_PROD}
```

### 2. Update Frontend Configuration

Update `/frontend/.env`:

```env
REACT_APP_EPIC_CLIENT_ID=0eb42959-ba12-4e23-81c9-0a523d40fd4a
REACT_APP_EPIC_REDIRECT_URI=https://localhost:3000/callback
REACT_APP_EPIC_SCOPE=launch patient/*.read user/*.read openid profile
```

### 3. Required Scopes for Your App

Based on your app's intended purposes, request these scopes:

```
# Patient Access
patient/Patient.read
patient/Encounter.read
patient/Observation.read
patient/Condition.read
patient/MedicationRequest.read
patient/AllergyIntolerance.read
patient/Procedure.read
patient/DocumentReference.read

# Clinical Team Access
user/Patient.read
user/Encounter.read
user/Encounter.write
user/Observation.read
user/Observation.write
user/MedicationRequest.read
user/MedicationRequest.write

# For AI Agent Actions
user/ServiceRequest.write
user/Task.write
user/CommunicationRequest.write
```

### 4. SMART App Launch Flow

Since your app uses SMART on FHIR with a redirect URI, implement the launch flow:

1. **EHR Launch**: Epic provides a launch parameter
2. **Authorization**: Redirect to Epic's authorization endpoint
3. **Callback**: Handle the callback at `https://localhost:3000/callback`
4. **Token Exchange**: Exchange authorization code for access token
5. **API Access**: Use token to access FHIR resources

### 5. AI Agent Integration Points

Your app can integrate AI agents at these points:

1. **Voice Commands**:
   - Capture audio from clinical team
   - Transcribe using Whisper API
   - Process commands with AI

2. **Automated Tasks**:
   - Patient summary generation
   - Order entry suggestions
   - Action plan proposals
   - Clinical documentation

3. **FHIR Resources for AI Actions**:
   ```json
   {
     "resourceType": "Task",
     "status": "requested",
     "intent": "order",
     "code": {
       "text": "AI-generated clinical summary"
     },
     "for": {
       "reference": "Patient/[id]"
     },
     "authoredOn": "2024-01-15T10:00:00Z",
     "requester": {
       "reference": "Practitioner/[id]"
     }
   }
   ```

## Testing Your Integration

### 1. Sandbox Testing

Use Epic's sandbox with test patients:

```javascript
// Test patient IDs
const testPatients = {
  'Jason Argonaut': 'Tbt3KuCY0B5PSrJvCu2j-PlK.aiHsu2xUjUM8bWpetXoB',
  'Jessica Argonaut': 'TUKRxL29bxE9lyAcdTIyrWC6Ln5gZ-z7CLr2r-2SY964B',
  'Derrick Lin': 'eq081-VQEgP8drUUqCWzHfw3'
};
```

### 2. Launch Testing

Test the SMART launch flow:

```bash
# 1. Initiate launch
GET https://localhost:3000/launch?iss=https://fhir.epic.com/interconnect-fhir-oauth/api/FHIR/R4&launch=YOUR_LAUNCH_TOKEN

# 2. Your app redirects to Epic auth
https://fhir.epic.com/interconnect-fhir-oauth/oauth2/authorize?
  response_type=code&
  client_id=0eb42959-ba12-4e23-81c9-0a523d40fd4a&
  redirect_uri=https://localhost:3000/callback&
  scope=launch patient/*.read user/*.read&
  state=RANDOM_STATE&
  aud=https://fhir.epic.com/interconnect-fhir-oauth/api/FHIR/R4

# 3. Epic redirects back with code
https://localhost:3000/callback?code=AUTH_CODE&state=RANDOM_STATE

# 4. Exchange code for token
POST https://fhir.epic.com/interconnect-fhir-oauth/oauth2/token
```

### 3. API Testing

Test FHIR API access:

```bash
# Get patient data
curl -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  https://fhir.epic.com/interconnect-fhir-oauth/api/FHIR/R4/Patient/Tbt3KuCY0B5PSrJvCu2j-PlK.aiHsu2xUjUM8bWpetXoB

# Search for conditions
curl -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  "https://fhir.epic.com/interconnect-fhir-oauth/api/FHIR/R4/Condition?patient=Tbt3KuCY0B5PSrJvCu2j-PlK.aiHsu2xUjUM8bWpetXoB"
```

## Security Considerations

1. **Client Secret**: Never expose in frontend code
2. **HTTPS Required**: Use HTTPS even for localhost testing
3. **Token Storage**: Store tokens securely, use refresh tokens
4. **Audit Logging**: Log all FHIR API access
5. **PHI Protection**: Encrypt all patient data at rest

## Next Steps

1. **Complete SMART Auth Implementation**:
   - Add OAuth2 callback handler
   - Implement token refresh logic
   - Handle launch context

2. **Test AI Agent Features**:
   - Voice command processing
   - Clinical summarization
   - Order entry automation

3. **Prepare for Production**:
   - Complete Epic's security assessment
   - Test with real clinical workflows
   - Get customer organization approval

4. **Monitor Usage**:
   - Track API calls
   - Monitor response times
   - Log AI agent actions

## Support

- Epic Developer Forum: https://galaxy.epic.com
- SMART on FHIR Docs: http://docs.smarthealthit.org/
- Your App Dashboard: https://fhir.epic.com/Developer/Apps