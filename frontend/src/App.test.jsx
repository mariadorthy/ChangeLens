import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import App from './App.jsx'

describe('ChangeLens dashboard', () => {
  it('renders the ChangeLens foundation UI', () => {
    render(<App />)

    expect(screen.getByRole('heading', { name: 'ChangeLens' })).toBeInTheDocument()
    expect(screen.getByText('Know what else needs to change.')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Analysis report' })).toBeInTheDocument()
  })
})
