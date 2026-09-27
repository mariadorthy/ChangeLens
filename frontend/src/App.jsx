import { useState } from 'react'
import { analyzeChanges } from './services/api.js'
import { AnalysisReport } from './components/AnalysisReport.jsx'
import logo from './assets/logo.png'

const INITIAL_FORM = {
  repository_url: '',
  base_revision: '',
  target_revision: '',
}

const ANALYSIS_STEPS = [
  'Reading Git changes',
  'Discovering relationships',
  'Checking completeness',
  'Building report',
]

export default function App() {
  const [form, setForm] = useState(INITIAL_FORM)
  const [report, setReport] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  function handleChange(event) {
    const { name, value } = event.target

    setForm((current) => ({
      ...current,
      [name]: value,
    }))
  }

  async function handleSubmit(event) {
    event.preventDefault()

    setLoading(true)
    setError(null)
    setReport(null)

    try {
      const result = await analyzeChanges(form)
      setReport(result)
    } catch (requestError) {
      setError(requestError)
    } finally {
      setLoading(false)
    }
  }

  function handleReset() {
    setForm(INITIAL_FORM)
    setReport(null)
    setError(null)
    setLoading(false)
  }

  const hasResult = report !== null || error !== null

  return (
    <main className="app-shell">
      <header className="hero">
          <div className="brand">
    <img src={logo} alt="ChangeLens Logo" className="logo" />

        <div>
          <p className="eyebrow">Developer workflow tool</p>
          <h1>ChangeLens</h1>
          <p className="tagline">Know what else needs to change.</p>
        </div>
</div>
        <span className="repository-status">Repository Analysis</span>
      </header>

      <section className="dashboard" aria-label="ChangeLens dashboard">
        <div className="section-heading">
          <div>
            <h2>Analyze a change</h2>
            <p className="muted">
  Give ChangeLens a public GitHub repository and two Git revisions.
  It identifies what changed, what is related, what was also updated,
  and what may still need attention.
</p>
          </div>
        </div>

        <form className="analysis-form" onSubmit={handleSubmit}>
            <div className="form-field">
  <label htmlFor="repository_url">GitHub Repository</label>

  <input
    id="repository_url"
    name="repository_url"
    type="url"
    value={form.repository_url}
    onChange={handleChange}
    placeholder="https://github.com/owner/repository"
    autoComplete="off"
    disabled={loading}
    aria-describedby="repository-url-help"
    required
  />

  <span id="repository-url-help" className="field-help">
    Public GitHub repository containing the Git revisions.
  </span>
</div>

          <div className="revision-grid">
            <div className="form-field">
              <label htmlFor="base_revision">Base Revision</label>
              <input
                id="base_revision"
                name="base_revision"
                type="text"
                value={form.base_revision}
                onChange={handleChange}
                placeholder="HEAD~1 or commit SHA"
                autoComplete="off"
                disabled={loading}
                aria-describedby="base-revision-help"
                required
              />
              <span id="base-revision-help" className="field-help">
                The earlier Git commit to compare from.
              </span>
            </div>

            <div className="form-field">
              <label htmlFor="target_revision">Target Revision</label>
              <input
                id="target_revision"
                name="target_revision"
                type="text"
                value={form.target_revision}
                onChange={handleChange}
                placeholder="HEAD or commit SHA"
                autoComplete="off"
                disabled={loading}
                aria-describedby="target-revision-help"
                required
              />
              <span id="target-revision-help" className="field-help">
                The later Git commit containing the change.
              </span>
            </div>
          </div>

          <div className="form-actions">
            <button
              className="primary-button"
              type="submit"
              disabled={loading}
            >
              {loading ? 'Analyzing...' : 'Analyze Changes'}
            </button>

            {hasResult && !loading && (
              <button
                className="secondary-button"
                type="button"
                onClick={handleReset}
              >
                Run Another Analysis
              </button>
            )}
          </div>
        </form>

        {loading && (
          <section
            className="loading-card"
            aria-live="polite"
            aria-label="Analysis in progress"
          >
                     <div className="loading-header">
              <span className="loading-spinner" aria-hidden="true" />
              <div>
                <h3>Analyzing repository...</h3>
                <p className="muted">
                  ChangeLens is running the analysis pipeline. The steps below
                  describe the work being performed.
                </p>
              </div>
            </div>

            <ol className="analysis-steps">
              {ANALYSIS_STEPS.map((step) => (
                <li key={step}>{step}</li>
              ))}
            </ol>
          </section>
        )}

        {error && (
          <section
            className="error-card"
            role="alert"
            aria-labelledby="analysis-error-title"
          >
            <div>
              <p className="status-label">Analysis could not be completed</p>
              <h3 id="analysis-error-title">{error.title}</h3>
              <p>{error.message}</p>
            </div>
          </section>
        )}

        {report && <AnalysisReport report={report} />}
      </section>
    </main>
  )
}
