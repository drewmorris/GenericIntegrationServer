import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

describe('Basic Test', () => {
  it('should pass a basic test', () => {
    const div = document.createElement('div');
    div.textContent = 'Hello World';
    expect(div.textContent).toBe('Hello World');
  });

  it('should render a simple component', () => {
    render(<div>Test Component</div>);
    expect(screen.getByText('Test Component')).toBeInTheDocument();
  });
});
