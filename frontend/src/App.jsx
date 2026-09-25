import { AnalysisReportPlaceholder } from './components/AnalysisReportPlaceholder.jsx'

export default function App() {
  return (
    <main className="app-shell">
      <section className="hero">
        <p className="eyebrow">Developer workflow tool</p>
        <h1>ChangeLens</h1>
        <p className="tagline">Know what else needs to change.</p>
      </section>

      <section className="dashboard" aria-label="ChangeLens dashboard">
        <div>
          <h2>Analysis dashboard</h2>
          <p className="muted">
            The analysis workflow will be connected here in a later phase.
          </p>
        </div>
        <AnalysisReportPlaceholder />
      </section>
    </main>
  )
}
