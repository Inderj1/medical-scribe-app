import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import ClinicalNotesPage from '../pages/ClinicalNotesPage';
import SpeakerIndicator from '../components/ClinicalNotes/SpeakerIndicator';
import AgentStatus from '../components/ClinicalNotes/AgentStatus';
import webSocketService from '../services/websocket';

// Mock WebSocket service
jest.mock('../services/websocket', () => ({
  connect: jest.fn(),
  disconnect: jest.fn(),
  emit: jest.fn(),
  on: jest.fn(),
  off: jest.fn(),
}));

// Mock router
jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => jest.fn(),
}));

// Mock contexts
jest.mock('../contexts/PatientContext', () => ({
  usePatient: () => ({
    selectedPatient: {
      id: 'test-patient-001',
      first_name: 'John',
      last_name: 'Doe',
      mrn: 'MRN001234',
      date_of_birth: '1978-05-15',
      gender: 'Male',
      age: 45,
    },
    selectedEncounter: {
      id: 'test-encounter-001',
      patient_id: 'test-patient-001',
      chief_complaint: 'General consultation',
      provider_name: 'Dr. Smith',
      encounter_date: new Date().toISOString(),
      encounter_type: 'Outpatient',
      status: 'In Progress',
    },
    recentVitals: {
      blood_pressure: '120/80',
      heart_rate: 72,
      respiratory_rate: 16,
      temperature: 98.6,
      oxygen_saturation: 98,
      pain_level: '0/10',
    },
  }),
}));

describe('ClinicalNotesPage', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('renders Start Clinical Notes button initially', () => {
    render(<ClinicalNotesPage />);
    
    const startButton = screen.getByRole('button', { name: /Start Clinical Notes/i });
    expect(startButton).toBeInTheDocument();
    expect(startButton).not.toBeDisabled();
  });

  test('shows loading state when Start Clinical Notes is clicked', async () => {
    render(<ClinicalNotesPage />);
    
    const startButton = screen.getByRole('button', { name: /Start Clinical Notes/i });
    fireEvent.click(startButton);
    
    expect(webSocketService.emit).toHaveBeenCalledWith('clinical_notes:start', {
      type: 'clinical_notes:start',
      patient_id: 'test-patient-001',
      encounter_type: 'routine_visit',
    });
    
    expect(startButton).toBeDisabled();
  });

  test('displays clinical notes interface after EHR data loads', async () => {
    const { rerender } = render(<ClinicalNotesPage />);
    
    // Simulate WebSocket event handler
    const handlers = {};
    (webSocketService.on as jest.Mock).mockImplementation((event, handler) => {
      handlers[event] = handler;
    });
    
    // Click start button
    const startButton = screen.getByRole('button', { name: /Start Clinical Notes/i });
    fireEvent.click(startButton);
    
    // Simulate EHR data received
    if (handlers['clinical_notes:prefill']) {
      handlers['clinical_notes:prefill']({
        type: 'clinical_notes:prefill',
        encounter_id: 'test-enc-001',
        patient_id: 'test-patient-001',
        data: {
          sections: {
            chief_complaint: 'General consultation',
            medications: ['Metformin 500mg', 'Lisinopril 10mg'],
            allergies: ['Penicillin'],
          },
        },
      });
    }
    
    rerender(<ClinicalNotesPage />);
    
    await waitFor(() => {
      expect(screen.queryByText(/Start Clinical Notes/i)).not.toBeInTheDocument();
    });
  });
});

describe('SpeakerIndicator', () => {
  test('displays doctor speaker correctly', () => {
    render(
      <SpeakerIndicator
        currentSpeaker="DOCTOR"
        confidence={0.95}
        isActive={true}
      />
    );
    
    expect(screen.getByText('DOCTOR')).toBeInTheDocument();
    expect(screen.getByText('95%')).toBeInTheDocument();
  });

  test('displays patient speaker correctly', () => {
    render(
      <SpeakerIndicator
        currentSpeaker="PATIENT"
        confidence={0.85}
        isActive={true}
      />
    );
    
    expect(screen.getByText('PATIENT')).toBeInTheDocument();
    expect(screen.getByText('85%')).toBeInTheDocument();
  });

  test('shows inactive state when not active', () => {
    render(
      <SpeakerIndicator
        currentSpeaker={null}
        confidence={0}
        isActive={false}
      />
    );
    
    expect(screen.getByText('Inactive')).toBeInTheDocument();
  });

  test('confidence bar color changes based on value', () => {
    const { container } = render(
      <SpeakerIndicator
        currentSpeaker="DOCTOR"
        confidence={0.45}
        isActive={true}
      />
    );
    
    const progressBar = container.querySelector('.MuiLinearProgress-bar');
    expect(progressBar).toHaveStyle({ backgroundColor: expect.stringContaining('error') });
  });
});

describe('AgentStatus', () => {
  const mockActiveAgents = [
    { section: 'chief_complaint', status: 'processing' as const, confidence: 0.8 },
    { section: 'medications', status: 'completed' as const, confidence: 0.95 },
  ];

  test('displays all section agents', () => {
    render(
      <AgentStatus
        activeAgents={mockActiveAgents}
        currentSection="chief_complaint"
        isProcessing={true}
      />
    );
    
    expect(screen.getByText('Chief Complaint')).toBeInTheDocument();
    expect(screen.getByText('Medications')).toBeInTheDocument();
    expect(screen.getByText('Physical Exam')).toBeInTheDocument();
    expect(screen.getByText('Assessment & Plan')).toBeInTheDocument();
  });

  test('shows processing indicator for active agents', () => {
    render(
      <AgentStatus
        activeAgents={mockActiveAgents}
        currentSection="chief_complaint"
        isProcessing={true}
      />
    );
    
    expect(screen.getByText('Processing...')).toBeInTheDocument();
    expect(screen.getByText('Active')).toBeInTheDocument();
  });

  test('displays completion status with checkmark', () => {
    render(
      <AgentStatus
        activeAgents={mockActiveAgents}
        currentSection="medications"
        isProcessing={false}
      />
    );
    
    // Check for completed icon (checkmark)
    const completedSections = screen.getAllByTestId('CheckCircleIcon');
    expect(completedSections.length).toBeGreaterThan(0);
  });

  test('highlights current section', () => {
    const { container } = render(
      <AgentStatus
        activeAgents={mockActiveAgents}
        currentSection="chief_complaint"
        isProcessing={true}
      />
    );
    
    // The current section should have a different background
    const listItems = container.querySelectorAll('.MuiListItem-root');
    let highlightedItem = null;
    
    listItems.forEach(item => {
      if (item.textContent?.includes('Chief Complaint')) {
        highlightedItem = item;
      }
    });
    
    expect(highlightedItem).toHaveStyle({ backgroundColor: expect.stringContaining('rgba') });
  });

  test('shows ready state when no agents active', () => {
    render(
      <AgentStatus
        activeAgents={[]}
        currentSection={undefined}
        isProcessing={false}
      />
    );
    
    expect(screen.getByText(/Agents ready/i)).toBeInTheDocument();
  });
});

describe('WebSocket Message Handling', () => {
  test('handles speaker identification updates', async () => {
    const handlers = {};
    (webSocketService.on as jest.Mock).mockImplementation((event, handler) => {
      handlers[event] = handler;
    });
    
    render(<ClinicalNotesPage />);
    
    // Simulate speaker identification
    if (handlers['speaker:identified']) {
      handlers['speaker:identified']({
        speaker: 'DOCTOR',
        confidence: 0.92,
      });
    }
    
    // Component should update with speaker info
    await waitFor(() => {
      expect(webSocketService.on).toHaveBeenCalledWith('speaker:identified', expect.any(Function));
    });
  });

  test('handles section updates from agents', async () => {
    const handlers = {};
    (webSocketService.on as jest.Mock).mockImplementation((event, handler) => {
      handlers[event] = handler;
    });
    
    render(<ClinicalNotesPage />);
    
    // Simulate section update
    if (handlers['section:update']) {
      handlers['section:update']({
        section: 'chief_complaint',
        content: 'Patient reports headache for 3 days',
        entities: [{ type: 'symptom', text: 'headache' }],
        confidence: 0.88,
      });
    }
    
    await waitFor(() => {
      expect(webSocketService.on).toHaveBeenCalledWith('section:update', expect.any(Function));
    });
  });
});