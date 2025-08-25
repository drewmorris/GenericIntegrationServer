import { AppBar, Button, MenuItem, Select, Toolbar, Typography } from '@mui/material';
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { useAuth } from '../context/AuthContext';

export default function TopNav() {
  const { logout } = useAuth();
  const navigate = useNavigate();
  const [orgId, setOrgId] = useState(localStorage.getItem('org_id') || 'default-org');
  useEffect(() => {
    localStorage.setItem('org_id', orgId);
  }, [orgId]);
  const handleLogout = () => {
    logout();
    navigate('/login');
  };
  return (
    <AppBar position="static" color="primary">
      <Toolbar>
        <Typography
          variant="h6"
          sx={{ flexGrow: 1 }}
          onClick={() => navigate('/')}
          style={{ cursor: 'pointer' }}
        >
          Integration Server
        </Typography>
        <Select
          size="small"
          value={orgId}
          onChange={(e) => setOrgId(e.target.value)}
          sx={{ mr: 2, color: 'white', '.MuiSelect-icon': { color: 'white' } }}
        >
          <MenuItem value={orgId}>{orgId}</MenuItem>
        </Select>
        <Button color="inherit" onClick={() => navigate('/profiles')} sx={{ mr: 1 }}>
          Profiles
        </Button>
        <Button color="inherit" onClick={() => navigate('/connectors')} sx={{ mr: 1 }}>
          Connectors
        </Button>
        <Button color="inherit" onClick={() => navigate('/destinations')} sx={{ mr: 1 }}>
          Destinations
        </Button>
        <Button color="inherit" onClick={() => navigate('/sync-monitoring')} sx={{ mr: 1 }}>
          Sync Monitor
        </Button>
        <Button color="inherit" onClick={handleLogout}>
          Logout
        </Button>
      </Toolbar>
    </AppBar>
  );
}
