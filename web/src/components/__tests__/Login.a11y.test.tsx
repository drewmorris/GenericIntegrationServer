/**
 * Basic accessibility tests
 * Tests WCAG compliance for common UI patterns
 */

import { render } from '@testing-library/react';
import { axe, toHaveNoViolations } from 'jest-axe';
import { describe, expect, it } from 'vitest';

// Extend expect with jest-axe matchers
expect.extend(toHaveNoViolations);

const TestForm = () => (
    <main>
        <form>
            <label htmlFor="email">Email</label>
            <input id="email" type="email" required />

            <label htmlFor="password">Password</label>
            <input id="password" type="password" required />

            <button type="submit">Sign In</button>
        </form>
    </main>
);

describe('Basic Components - Accessibility', () => {
    it('should not have any accessibility violations for form', async () => {
        const { container } = render(<TestForm />);
        const results = await axe(container);
        expect(results).toHaveNoViolations();
    });

    it('should have proper ARIA labels and roles', () => {
        const { getByRole, getByLabelText } = render(<TestForm />);

        // Check for proper form structure
        expect(getByRole('main')).toBeInTheDocument();
        expect(getByRole('button', { name: /sign in/i })).toBeInTheDocument();

        // Check for accessible form inputs
        expect(getByLabelText(/email/i)).toBeInTheDocument();
        expect(getByLabelText(/password/i)).toBeInTheDocument();
    });

    it('should be keyboard navigable', () => {
        const { getByRole } = render(<TestForm />);
        const signInButton = getByRole('button', { name: /sign in/i });

        // Check that interactive elements are focusable
        expect(signInButton).not.toHaveAttribute('tabindex', '-1');
    });
});
