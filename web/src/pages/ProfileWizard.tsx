// @ts-nocheck
import { useState } from 'react';
import { Stepper, Step, StepLabel, Button, TextField, Container, MenuItem, Typography } from '@mui/material';
import { useCreateProfile } from '../hooks/useCreateProfile';
import { useNavigate } from 'react-router-dom';
import { v4 as uuidv4 } from 'uuid';
import { useSnack } from '../components/Snackbar';

const steps = ['Basics', 'Destination', 'Review'];

export default function ProfileWizard() {
    const [activeStep, setActiveStep] = useState(0);
    const [name, setName] = useState('');
    const [source, setSource] = useState('mock_source');
    const [destination, setDestination] = useState('cleverbrag');
    const { mutateAsync, isLoading } = useCreateProfile();
    const snack = useSnack();
    const navigate = useNavigate();

    const handleNext = async () => {
        if (activeStep === steps.length - 1) {
            const orgId = localStorage.getItem('org_id') || uuidv4();
            const userId = localStorage.getItem('user_id') || uuidv4();
            await mutateAsync({
                organization_id: orgId,
                user_id: userId,
                name,
                source,
                interval_minutes: 60,
                connector_config: { destination },
            });
            navigate('/profiles');
            snack.enqueue('Profile created', { variant: 'success' });
        } else {
            setActiveStep((s) => s + 1);
        }
    };
    const handleBack = () => setActiveStep((s) => s - 1);

    return (
        <Container maxWidth="sm" sx={{ mt: 4 }}>
            <Stepper activeStep={activeStep} alternativeLabel>
                {steps.map((label) => (
                    <Step key={label}><StepLabel>{label}</StepLabel></Step>
                ))}
            </Stepper>
            {activeStep === 0 && (
                <TextField fullWidth label="Profile Name" margin="normal" value={name} onChange={e => setName(e.target.value)} />
            )}
            {activeStep === 1 && (
                <TextField select fullWidth label="Destination" margin="normal" value={destination} onChange={e => setDestination(e.target.value)}>
                    <MenuItem value="cleverbrag">CleverBrag</MenuItem>
                    <MenuItem value="onyx">Onyx</MenuItem>
                    <MenuItem value="csv">CSV Dump</MenuItem>
                </TextField>
            )}
            {activeStep === 2 && (
                <Typography sx={{ mt: 2 }}>Ready to create profile "{name}" → {destination}</Typography>
            )}
            <Button disabled={activeStep === 0} onClick={handleBack} sx={{ mt: 2, mr: 1 }}>Back</Button>
            <Button variant="contained" onClick={handleNext} sx={{ mt: 2 }} disabled={isLoading}>{activeStep === steps.length - 1 ? 'Create' : 'Next'}</Button>
        </Container>
    );
} 