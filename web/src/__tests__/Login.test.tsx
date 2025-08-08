// @ts-nocheck
import { render, screen } from '@testing-library/react';
import Login from '../pages/Login';
import { BrowserRouter } from 'react-router-dom';

it('renders login heading', () => {
    render(
        <BrowserRouter>
            <Login />
        </BrowserRouter>,
    );
    expect(screen.getByText(/login/i)).toBeInTheDocument();
}); 