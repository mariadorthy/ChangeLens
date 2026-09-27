const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000'
  
export async function getHealth() {
  const response = await fetch(`${API_BASE_URL}/api/health`)

  if (!response.ok) {
    throw new Error(`Health request failed: ${response.status}`)
  }

  return response.json()
}

export async function analyzeChanges(request) {
  let response

  try {
    response = await fetch(`${API_BASE_URL}/api/analyze`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    })
  } catch {
    throw {
      title: 'Unable to reach ChangeLens backend.',
      message: 'Check that the backend is running and try again.',
    }
  }

  let body = null

  try {
    body = await response.json()
  } catch {
    body = null
  }

  if (!response.ok) {
    if (body?.detail?.message) {
      throw {
        title: 'Invalid repository or Git revision.',
        message: body.detail.message,
      }
    }

    throw {
      title: 'The analysis request failed.',
      message: 'ChangeLens returned an unexpected error. Try again.',
    }
  }

  if (
    !body ||
    !Array.isArray(body.changed_files) ||
    !Array.isArray(body.affected_and_changed) ||
    !Array.isArray(body.potentially_missing) ||
    !Array.isArray(body.validation_recommendations) ||
    typeof body.status !== 'string'
  ) {
    throw {
      title: 'Unexpected analysis response.',
      message: 'The backend returned data the dashboard could not understand.',
    }
  }

  return body
}

