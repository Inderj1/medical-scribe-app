const axios = require('axios');

// Test the patient search functionality
async function testPatientSearch() {
  const API_BASE_URL = 'http://localhost:8000';
  const EHRBASE_PROXY_URL = `${API_BASE_URL}/api/ehrbase/proxy`;
  
  console.log('=== Testing Patient Search with Real EHRBASE Data ===');
  
  try {
    // Test 1: Direct AQL query to get all EHRs
    console.log('\n1. Testing AQL query to get all EHRs...');
    const aqlResponse = await axios.post(`${EHRBASE_PROXY_URL}/query/aql`, {
      q: 'SELECT e/ehr_id/value as ehrId, e/ehr_status/subject/external_ref/id/value as subjectId FROM EHR e'
    });
    
    console.log('AQL query response:', aqlResponse.data);
    
    if (aqlResponse.data.rows && aqlResponse.data.rows.length > 0) {
      console.log(`✓ Found ${aqlResponse.data.rows.length} EHRs in EHRBASE`);
      
      // Test 2: Try to get compositions for the first EHR
      const firstEhrId = aqlResponse.data.rows[0][0];
      console.log(`\n2. Testing compositions for EHR: ${firstEhrId}`);
      
      const compositionsQuery = `
        SELECT 
          c/uid/value as compositionId,
          c/name/value as compositionName,
          c/archetype_details/archetype_id/value as archetypeId
        FROM EHR e
        CONTAINS COMPOSITION c
        WHERE e/ehr_id/value = '${firstEhrId}'
      `;
      
      const compositionsResponse = await axios.post(`${EHRBASE_PROXY_URL}/query/aql`, {
        q: compositionsQuery
      });
      
      console.log('Compositions response:', compositionsResponse.data);
      
      if (compositionsResponse.data.rows && compositionsResponse.data.rows.length > 0) {
        console.log(`✓ Found ${compositionsResponse.data.rows.length} compositions in first EHR`);
      } else {
        console.log('⚠ No compositions found - EHRs exist but no patient data stored');
      }
    } else {
      console.log('⚠ No EHRs found in EHRBASE');
    }
    
    // Test 3: Try to get templates
    console.log('\n3. Testing templates endpoint...');
    const templatesResponse = await axios.get(`${EHRBASE_PROXY_URL}/definition/template/adl1.4`);
    console.log('Templates response:', templatesResponse.data);
    
    if (Array.isArray(templatesResponse.data)) {
      console.log(`✓ Found ${templatesResponse.data.length} templates`);
    } else {
      console.log('⚠ No templates found or unexpected response format');
    }
    
    console.log('\n=== Test Complete ===');
    
  } catch (error) {
    console.error('Test failed:', error.message);
    if (error.response) {
      console.error('Response status:', error.response.status);
      console.error('Response data:', error.response.data);
    }
  }
}

// Run the test
testPatientSearch();