# Testing Guide for Agent-Based Medical Scribe System

## Overview
This directory contains comprehensive tests for the agent-based medical scribe system, including speaker diarization, section-specific agents, and the orchestration layer.

## Test Structure

### Unit Tests
- `test_speaker_diarization_agent.py` - Tests speaker identification (doctor vs patient)
- `test_section_agents.py` - Tests section-specific content processing
- `test_agent_orchestrator.py` - Tests routing and orchestration logic

### Quick Tests
- `quick_test.py` - Rapid verification of core components

### Test Runner
- `run_tests.py` - Comprehensive test execution and reporting

## Running Tests

### Quick Verification
```bash
# Run quick tests to verify basic functionality
cd backend/tests
python quick_test.py
```

### Full Test Suite
```bash
# Run all unit tests
pytest -v

# Run specific test file
pytest test_speaker_diarization_agent.py -v

# Run with coverage
pytest --cov=app tests/
```

### Test Runner
```bash
# Execute comprehensive test suite with reporting
python run_tests.py
```

## Test Categories

### 1. Speaker Diarization Tests
- Clear doctor speech patterns
- Clear patient speech patterns
- Ambiguous phrases
- Context-aware identification
- Performance benchmarks

### 2. Section Agent Tests
- Chief complaint processing
- Medications extraction
- Physical exam documentation
- Assessment and plan generation
- Format consistency (long/short/bullet)

### 3. Orchestration Tests
- Routing decisions
- Multi-agent coordination
- Context management
- Re-summarization triggers
- Concurrent encounter handling

### 4. Integration Tests
- WebSocket communication
- EHR data prefilling
- Real-time UI updates
- End-to-end workflows

## Expected Results

### Success Criteria
- Speaker identification accuracy: >85%
- Agent routing accuracy: >90%
- Processing latency: <2 seconds
- Concurrent encounters: 50+
- Test coverage: >85%

### Performance Benchmarks
- Speaker identification: <500ms
- Section processing: <2s
- Full transcription flow: <3s

## Test Data

### Sample Conversations
Located in test files, includes:
- Doctor-patient dialogues
- Medical terminology
- Ambiguous phrases
- Edge cases

### Mock Patients
```python
{
    "id": "test-patient-001",
    "name": "John Doe",
    "mrn": "MRN001234",
    "conditions": ["Diabetes", "Hypertension"],
    "medications": ["Metformin", "Lisinopril"]
}
```

## Debugging Failed Tests

### Common Issues

1. **OpenAI API Key Missing**
   ```bash
   export OPENAI_API_KEY="your-key-here"
   ```

2. **Import Errors**
   ```bash
   pip install -r requirements.txt
   pip install openai-agents
   ```

3. **Async Test Failures**
   Ensure using `pytest-asyncio`:
   ```bash
   pip install pytest-asyncio
   ```

## CI/CD Integration

### GitHub Actions
```yaml
- name: Run Tests
  run: |
    cd backend
    pytest tests/ -v --cov=app
```

### Pre-commit Hook
```bash
#!/bin/sh
cd backend && python tests/quick_test.py
```

## Test Reports

Test results are saved to:
- `test_report.json` - Detailed results
- Console output - Summary statistics

## Contributing

When adding new features:
1. Write unit tests first (TDD)
2. Ensure >80% coverage
3. Add integration tests
4. Update this README

## Troubleshooting

### Test Timeouts
- Increase timeout in pytest.ini
- Check API rate limits
- Verify network connectivity

### Flaky Tests
- Use retry logic for API calls
- Mock external dependencies
- Set consistent random seeds

### Memory Issues
- Run tests in smaller batches
- Use pytest-xdist for parallel execution
- Monitor resource usage

## Next Steps

After tests pass:
1. Deploy to staging environment
2. Run load tests
3. Perform user acceptance testing
4. Monitor production metrics