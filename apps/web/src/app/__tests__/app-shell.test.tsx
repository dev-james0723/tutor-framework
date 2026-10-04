import { render, screen } from '@testing-library/react';
import { expect, test, vi } from 'vitest';
import Home from '../page';
test('shell offers a first learning action without network or model availability', () => {
  const network = vi.spyOn(globalThis, 'fetch').mockImplementation(() => { throw new Error('offline'); });
  render(<Home />);
  expect(screen.getByRole('heading', { name: 'Super Theory Tutor' })).toBeVisible();
  expect(screen.getByRole('link', { name: 'Start learning' })).toHaveAttribute('href', '/sign-up');
  expect(network).not.toHaveBeenCalled();
  network.mockRestore();
});
