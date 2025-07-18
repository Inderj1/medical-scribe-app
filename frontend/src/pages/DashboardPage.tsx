import React from 'react';
import { Box, Grid, Paper, Typography, Card, CardContent } from '@mui/material';
import { 
  People as PeopleIcon, 
  Description as DescriptionIcon, 
  Assignment as AssignmentIcon,
  TrendingUp as TrendingUpIcon 
} from '@mui/icons-material';

interface StatCard {
  title: string;
  value: string | number;
  icon: React.ReactNode;
  color: string;
}

function DashboardPage() {
  const stats: StatCard[] = [
    {
      title: 'Total Patients',
      value: '1,234',
      icon: <PeopleIcon sx={{ fontSize: 40 }} />,
      color: '#3f51b5'
    },
    {
      title: 'Active Encounters',
      value: '48',
      icon: <AssignmentIcon sx={{ fontSize: 40 }} />,
      color: '#4caf50'
    },
    {
      title: 'Transcriptions Today',
      value: '156',
      icon: <DescriptionIcon sx={{ fontSize: 40 }} />,
      color: '#ff9800'
    },
    {
      title: 'Avg. Documentation Time',
      value: '3.2 min',
      icon: <TrendingUpIcon sx={{ fontSize: 40 }} />,
      color: '#f44336'
    }
  ];

  return (
    <Box>
      <Typography variant="h4" gutterBottom sx={{ mb: 4 }}>
        Dashboard
      </Typography>

      {/* Statistics Cards */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        {stats.map((stat, index) => (
          <Grid item xs={12} sm={6} md={3} key={index}>
            <Card elevation={3}>
              <CardContent>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <Box>
                    <Typography color="textSecondary" gutterBottom variant="body2">
                      {stat.title}
                    </Typography>
                    <Typography variant="h4" component="h2">
                      {stat.value}
                    </Typography>
                  </Box>
                  <Box sx={{ color: stat.color }}>
                    {stat.icon}
                  </Box>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      {/* Recent Activity */}
      <Grid container spacing={3}>
        <Grid item xs={12} md={8}>
          <Paper elevation={2} sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Recent Encounters
            </Typography>
            <Box sx={{ mt: 2 }}>
              {[1, 2, 3, 4, 5].map((item) => (
                <Box 
                  key={item} 
                  sx={{ 
                    py: 2, 
                    borderBottom: '1px solid #e0e0e0',
                    '&:last-child': { borderBottom: 'none' }
                  }}
                >
                  <Typography variant="subtitle1">
                    Patient #{1000 + item} - John Doe
                  </Typography>
                  <Typography variant="body2" color="textSecondary">
                    Chief Complaint: General checkup • Dr. Smith • 2 hours ago
                  </Typography>
                </Box>
              ))}
            </Box>
          </Paper>
        </Grid>

        <Grid item xs={12} md={4}>
          <Paper elevation={2} sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              System Alerts
            </Typography>
            <Box sx={{ mt: 2 }}>
              <Box sx={{ py: 1 }}>
                <Typography variant="body2" color="success.main">
                  ✓ All systems operational
                </Typography>
              </Box>
              <Box sx={{ py: 1 }}>
                <Typography variant="body2" color="info.main">
                  ℹ️ Scheduled maintenance: Tomorrow 2 AM
                </Typography>
              </Box>
              <Box sx={{ py: 1 }}>
                <Typography variant="body2" color="warning.main">
                  ⚠️ 5 transcriptions pending review
                </Typography>
              </Box>
            </Box>
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
}

export default DashboardPage;