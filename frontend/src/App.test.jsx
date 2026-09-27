import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import App from './App.jsx'

const COMPLETE_RESPONSE = {
  status: 'complete',
  changed_files: ['README.md'],
  affected_and_changed: [],
  potentially_missing: [],
  validation_recommendations: [],
}

const INCOMPLETE_RESPONSE = {
  status: 'potentially_incomplete',
  changed_files: ['backend/services/task_service.py'],
  affected_and_changed: [],
  potentially_missing: [
    {
      path: 'backend/api/tasks.py',
      relationship_types: ['reference'],
      reasons: ['References symbol(s): get_tasks'],
      confidences: ['medium'],
      statuses: [],
    },
  ],
  validation_recommendations: ['Review affected source references'],
}

function fillForm() {
  fireEvent.change(screen.getByLabelText('Repository Path'), {
    target: {
      value: 'D:\\projects\\change-completeness-analyzer',
    },
  })

  fireEvent.change(screen.getByLabelText('Base Revision'), {
    target: {
      value: 'abc123',
    },
  })

  fireEvent.change(screen.getByLabelText('Target Revision'), {
    target: {
      value: 'def456',
    },
  })
}

describe('ChangeLens dashboard', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('renders the initial empty state and form', () => {
    render(<App />)

    expect(screen.getByRole('heading', { name: 'ChangeLens' })).toBeInTheDocument()
    expect(
      screen.getByText('Know what else needs to change.'),
    ).toBeInTheDocument()

    expect(
      screen.getByRole('heading', { name: 'Analyze a change' }),
    ).toBeInTheDocument()

    expect(screen.getByLabelText('Repository Path')).toBeInTheDocument()
    expect(screen.getByLabelText('Base Revision')).toBeInTheDocument()
    expect(screen.getByLabelText('Target Revision')).toBeInTheDocument()
    expect(
      screen.getByRole('button', { name: 'Analyze Changes' }),
    ).toBeInTheDocument()
  })

  it('submits the analysis and renders a complete result', async () => {
    const fetchMock = vi
      .spyOn(globalThis, 'fetch')
      .mockResolvedValue(
        new Response(JSON.stringify(COMPLETE_RESPONSE), {
          status: 200,
          headers: {
            'Content-Type': 'application/json',
          },
        }),
      )

    render(<App />)
    fillForm()

    fireEvent.click(
      screen.getByRole('button', { name: 'Analyze Changes' }),
    )

    expect(
      screen.getByText('Analyzing repository...'),
    ).toBeInTheDocument()
    expect(screen.getByText('Reading Git changes')).toBeInTheDocument()
    expect(screen.getByText('Discovering relationships')).toBeInTheDocument()
    expect(screen.getByText('Checking completeness')).toBeInTheDocument()
    expect(screen.getByText('Building report')).toBeInTheDocument()
    await waitFor(() => {
      expect(
        screen.getByRole('heading', { name: 'Complete' }),
      ).toBeInTheDocument()
    })

    expect(screen.getByText('README.md')).toBeInTheDocument()
        expect(
      screen.getAllByText('No potentially missing artifacts detected.'),
    ).toHaveLength(1)
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining('/analyze'),
      expect.objectContaining({
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      }),
    )
  })

  it('renders potentially missing artifacts and recommendations', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify(INCOMPLETE_RESPONSE), {
        status: 200,
        headers: {
          'Content-Type': 'application/json',
        },
      }),
    )

    render(<App />)
    fillForm()

    fireEvent.click(
      screen.getByRole('button', { name: 'Analyze Changes' }),
    )

    await waitFor(() => {
      expect(
        screen.getByRole('heading', { name: 'Potentially Incomplete' }),
      ).toBeInTheDocument()
    })

    expect(
      screen.getByText('backend/services/task_service.py'),
    ).toBeInTheDocument()

    expect(
      screen.getByText('backend/api/tasks.py'),
    ).toBeInTheDocument()

    expect(
      screen.getByText('References symbol(s): get_tasks'),
    ).toBeInTheDocument()

    const badge = screen.getByText('medium')
    expect(badge).toBeInTheDocument()
    expect(badge).toHaveClass('confidence-badge', 'medium')
    expect(
      screen.getByText('Review affected source references'),
    ).toBeInTheDocument()
  })

  it('renders the confidence badge with the correct class for each level', async () => {
    const highConfidenceResponse = {
      ...COMPLETE_RESPONSE,
      potentially_missing: [
        {
          path: 'some/file.py',
          relationship_types: ['reference'],
          reasons: ['References symbol(s): foo'],
          confidences: ['high'],
          statuses: [],
        },
      ],
    }

    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify(highConfidenceResponse), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )

    render(<App />)
    fillForm()
    fireEvent.click(screen.getByRole('button', { name: 'Analyze Changes' }))

    await waitFor(() => {
      expect(screen.getByText('high')).toBeInTheDocument()
    })

    const badge = screen.getByText('high')
    expect(badge).toHaveClass('confidence-badge', 'high')
  })

  it('renders affected and changed artifacts', async () => {
    const response = {
      ...COMPLETE_RESPONSE,
      affected_and_changed: [
        {
          path: 'tests/test_task_service.py',
          relationship_types: ['test'],
          reasons: ['References changed module'],
          confidences: ['high'],
          statuses: [],
        },
      ],
    }

    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify(response), {
        status: 200,
        headers: {
          'Content-Type': 'application/json',
        },
      }),
    )

    render(<App />)
    fillForm()

    fireEvent.click(
      screen.getByRole('button', { name: 'Analyze Changes' }),
    )

    await waitFor(() => {
      expect(
        screen.getByRole('heading', { name: 'Affected & Changed' }),
      ).toBeInTheDocument()
    })

    expect(
      screen.getByText('tests/test_task_service.py'),
    ).toBeInTheDocument()

    expect(screen.getByText('References changed module')).toBeInTheDocument()
    expect(screen.getByText('high')).toBeInTheDocument()
  })

  it('renders an API error clearly', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(
        JSON.stringify({
          detail: {
            code: 'invalid_repository_or_revision',
            message: 'Invalid target revision: does-not-exist',
          },
        }),
        {
          status: 400,
          headers: {
            'Content-Type': 'application/json',
          },
        },
      ),
    )

    render(<App />)
    fillForm()

    fireEvent.click(
      screen.getByRole('button', { name: 'Analyze Changes' }),
    )

    await waitFor(() => {
      expect(
        screen.getByText('Analysis could not be completed'),
      ).toBeInTheDocument()
    })

    expect(
      screen.getByText('Invalid target revision: does-not-exist'),
    ).toBeInTheDocument()
  })

  it('renders a network error when the backend cannot be reached', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(
      new Error('Failed to fetch'),
    )

    render(<App />)
    fillForm()

    fireEvent.click(
      screen.getByRole('button', { name: 'Analyze Changes' }),
    )

    await waitFor(() => {
      expect(
        screen.getByText('Unable to reach ChangeLens backend.'),
      ).toBeInTheDocument()
    })

    expect(
      screen.getByText(
        'Check that the backend is running and try again.',
      ),
    ).toBeInTheDocument()
  })

  it('disables the analyze button while the request is running', async () => {
    let resolveRequest

    const pendingRequest = new Promise((resolve) => {
      resolveRequest = resolve
    })

    vi.spyOn(globalThis, 'fetch').mockReturnValue(pendingRequest)

    render(<App />)
    fillForm()

    fireEvent.click(
      screen.getByRole('button', { name: 'Analyze Changes' }),
    )

    const button = screen.getByRole('button', { name: 'Analyzing...' })

    expect(button).toBeDisabled()
    expect(screen.getByLabelText('Repository Path')).toBeDisabled()

    resolveRequest(
      new Response(JSON.stringify(COMPLETE_RESPONSE), {
        status: 200,
        headers: {
          'Content-Type': 'application/json',
        },
      }),
    )

    await waitFor(() => {
      expect(
        screen.getByRole('heading', { name: 'Complete' }),
      ).toBeInTheDocument()
    })
  })

  it('allows the user to reset and run another analysis', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify(COMPLETE_RESPONSE), {
        status: 200,
        headers: {
          'Content-Type': 'application/json',
        },
      }),
    )

    render(<App />)
    fillForm()

    fireEvent.click(
      screen.getByRole('button', { name: 'Analyze Changes' }),
    )

    await waitFor(() => {
      expect(
        screen.getByRole('heading', { name: 'Complete' }),
      ).toBeInTheDocument()
    })

    fireEvent.click(
      screen.getByRole('button', { name: 'Run Another Analysis' }),
    )

    expect(screen.getByLabelText('Repository Path')).toHaveValue('')
    expect(screen.getByLabelText('Base Revision')).toHaveValue('')
    expect(screen.getByLabelText('Target Revision')).toHaveValue('')

        expect(
      screen.getByRole('button', { name: 'Analyze Changes' }),
    ).toBeInTheDocument()

    expect(
      screen.getByText(
        'Local path to the Git repository that contains the change.',
      ),
    ).toBeInTheDocument()

    expect(
      screen.getByText('The earlier Git commit to compare from.'),
    ).toBeInTheDocument()

    expect(
      screen.getByText('The later Git commit containing the change.'),
    ).toBeInTheDocument()

    expect(
      screen.queryByRole('heading', { name: 'Complete' }),
    ).not.toBeInTheDocument()
  })
})