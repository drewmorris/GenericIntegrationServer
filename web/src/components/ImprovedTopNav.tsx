import {
  Cable as CableIcon,
  Dashboard as DashboardIcon,
  Info as InfoIcon,
  Logout as LogoutIcon,
  Person as PersonIcon,
  Send as SendIcon,
  Settings as SettingsIcon,
  Timeline as TimelineIcon,
} from '@mui/icons-material';
import {
  AppBar,
  Avatar,
  Box,
  Button,
  Chip,
  Divider,
  ListItemIcon,
  ListItemText,
  Menu,
  MenuItem,
  Toolbar,
  Tooltip,
  Typography,
} from '@mui/material';
import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';

import { useAuth } from '../context/AuthContext';
import { api } from '../lib/api';

interface Organization {
  id: string;
  name: string;
  created_at: string;
  billing_plan?: string;
}

interface User {
  id: string;
  email: string;
  organization: Organization;
  organization_id: string;
}

export default function ImprovedTopNav() {
  const { logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [userMenuAnchor, setUserMenuAnchor] = useState<null | HTMLElement>(null);

  // Fetch current user info including organization name
  const { data: userInfo } = useQuery<User>({
    queryKey: ['current-user'],
    queryFn: async () => {
      const { data } = await api.get<User>('/users/me');
      return data;
    },
    staleTime: 10 * 60 * 1000, // Cache for 10 minutes
  });

  const handleLogout = () => {
    logout();
    navigate('/login');
    setUserMenuAnchor(null);
  };

  const handleUserMenuOpen = (event: React.MouseEvent<HTMLElement>) => {
    setUserMenuAnchor(event.currentTarget);
  };

  const handleUserMenuClose = () => {
    setUserMenuAnchor(null);
  };

  const isActive = (path: string) => location.pathname === path;

  const navigationItems = [
    {
      label: 'Dashboard',
      path: '/',
      icon: <DashboardIcon />,
      description: 'Overview and getting started guide',
      color: 'primary' as const,
    },
    {
      label: 'Destinations',
      path: '/destinations',
      icon: <SendIcon />,
      description: 'Configure where your data goes (CleverBrag, etc.)',
      color: 'secondary' as const,
    },
    {
      label: 'Connectors',
      path: '/connectors',
      icon: <CableIcon />,
      description: 'Set up data sources (Google Drive, Slack, etc.)',
      color: 'info' as const,
    },
    {
      label: 'Profiles',
      path: '/profiles',
      icon: <PersonIcon />,
      description: 'Manage authentication credentials',
      color: 'warning' as const,
    },
    {
      label: 'Sync Monitor',
      path: '/sync-monitoring',
      icon: <TimelineIcon />,
      description: 'Real-time sync progress and monitoring',
      color: 'success' as const,
    },
  ];

  return (
    <AppBar position="static" color="primary">
      <Toolbar>
        {/* Logo and Title */}
        <Box
          display="flex"
          alignItems="center"
          sx={{ cursor: 'pointer' }}
          onClick={() => navigate('/')}
        >
          <Typography variant="h6" sx={{ fontWeight: 'bold' }}>
            Integration Server
          </Typography>
        </Box>

        {/* Organization Info */}
        <Box sx={{ ml: 2, display: 'flex', alignItems: 'center' }}>
          <Tooltip title="Current Organization">
            <Chip
              label={userInfo?.organization?.name || 'Loading...'}
              variant="outlined"
              sx={{
                color: 'white',
                borderColor: 'rgba(255,255,255,0.3)',
                '& .MuiChip-label': { color: 'white' },
              }}
            />
          </Tooltip>
        </Box>

        <Box sx={{ flexGrow: 1 }} />

        {/* Navigation Items */}
        <Box sx={{ display: 'flex', gap: 1 }}>
          {navigationItems.map((item) => (
            <Tooltip key={item.path} title={item.description} placement="bottom">
              <Button
                color="inherit"
                onClick={() => navigate(item.path)}
                startIcon={item.icon}
                variant={isActive(item.path) ? 'outlined' : 'text'}
                sx={{
                  borderColor: isActive(item.path) ? 'rgba(255,255,255,0.5)' : 'transparent',
                  backgroundColor: isActive(item.path) ? 'rgba(255,255,255,0.1)' : 'transparent',
                  '&:hover': {
                    backgroundColor: 'rgba(255,255,255,0.1)',
                  },
                }}
              >
                {item.label}
              </Button>
            </Tooltip>
          ))}
        </Box>

        {/* User Menu */}
        <Box sx={{ ml: 2 }}>
          <Tooltip title="Account settings">
            <Button
              color="inherit"
              onClick={handleUserMenuOpen}
              startIcon={
                <Avatar sx={{ width: 24, height: 24 }}>
                  {userInfo?.email?.[0]?.toUpperCase()}
                </Avatar>
              }
              sx={{ textTransform: 'none' }}
            >
              {userInfo?.email?.split('@')[0] || 'User'}
            </Button>
          </Tooltip>
          <Menu
            anchorEl={userMenuAnchor}
            open={Boolean(userMenuAnchor)}
            onClose={handleUserMenuClose}
            transformOrigin={{ horizontal: 'right', vertical: 'top' }}
            anchorOrigin={{ horizontal: 'right', vertical: 'bottom' }}
          >
            <MenuItem disabled>
              <ListItemText primary={userInfo?.email} secondary={userInfo?.organization?.name} />
            </MenuItem>
            <Divider />
            <MenuItem
              onClick={() => {
                navigate('/api-keys');
                handleUserMenuClose();
              }}
            >
              <ListItemIcon>
                <SettingsIcon fontSize="small" />
              </ListItemIcon>
              <ListItemText primary="API Keys" />
            </MenuItem>
            <MenuItem
              onClick={() => {
                window.open('http://localhost:8000/docs', '_blank');
                handleUserMenuClose();
              }}
            >
              <ListItemIcon>
                <InfoIcon fontSize="small" />
              </ListItemIcon>
              <ListItemText primary="API Documentation" />
            </MenuItem>
            <Divider />
            <MenuItem onClick={handleLogout}>
              <ListItemIcon>
                <LogoutIcon fontSize="small" />
              </ListItemIcon>
              <ListItemText primary="Logout" />
            </MenuItem>
          </Menu>
        </Box>
      </Toolbar>
    </AppBar>
  );
}
