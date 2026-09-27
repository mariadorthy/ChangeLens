function CountCard({ label, value }) {
  return (
    <div className="summary-card">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  )
}

function ArtifactCard({ artifact, variant }) {
  return (
    <article className={`artifact-card artifact-${variant}`}>
      <div className="artifact-header">
        <span className="artifact-icon" aria-hidden="true">
          {variant === 'missing' ? '!' : '✓'}
        </span>
        <code>{artifact.path}</code>
      </div>

      {artifact.relationship_types?.length > 0 && (
        <div className="artifact-detail">
          <span className="detail-label">Relationship</span>
          <span>{artifact.relationship_types.join(', ')}</span>
        </div>
      )}

      {artifact.reasons?.length > 0 && (
        <div className="artifact-detail">
          <span className="detail-label">Evidence</span>
          <span>{artifact.reasons.join(' · ')}</span>
        </div>
      )}

      {artifact.confidences?.length > 0 && (
        <div className="artifact-detail">
          <span className="detail-label">Confidence</span>
          <span>
            {artifact.confidences.map((confidence) => (
              <span
                key={confidence}
                className={`confidence-badge ${confidence.toLowerCase()}`}
              >
                {confidence}
              </span>
            ))}
          </span>
        </div>
      )}
    </article>
  )
}

function ChangedFileCard({ path }) {
  return (
    <article className="changed-file">
      <div className="changed-file-main">
        <span className="file-check" aria-hidden="true">
          ✓
        </span>
        <code>{path}</code>
      </div>
    </article>
  )
}

export function AnalysisReport({ report }) {
  const isComplete = report.status === 'complete'
  const statusLabel = isComplete ? 'Complete' : 'Potentially Incomplete'

  return (
    <section
      className="analysis-result"
      aria-labelledby="analysis-result-title"
    >
      <div className={`status-banner ${isComplete ? 'status-complete' : 'status-warning'}`}>
        <span className="status-symbol" aria-hidden="true">
          {isComplete ? '✓' : '!'}
        </span>

        <div>
          <p className="status-label">Analysis Result</p>
          <h2 id="analysis-result-title">{statusLabel}</h2>

                    <p>
            {isComplete
              ? 'No potentially missing artifacts detected.'
              : 'Related artifacts were detected that were not included in the change.'}
          </p>
        </div>
      </div>

      <div className="summary-grid" aria-label="Analysis summary">
        <CountCard
          label="Changed Files"
          value={report.changed_files.length}
        />
        <CountCard
          label="Affected & Changed"
          value={report.affected_and_changed.length}
        />
        <CountCard
          label="Potentially Missing"
          value={report.potentially_missing.length}
        />
      </div>

      <section className="result-section" aria-labelledby="changed-files-title">
        <div className="result-section-heading">
          <div>
            <h3 id="changed-files-title">Changed Files</h3>
            <p className="muted">
              Files returned by the Git comparison.
            </p>
          </div>
        </div>

        {report.changed_files.length > 0 ? (
          <div className="file-list">
            {report.changed_files.map((path) => (
              <ChangedFileCard key={path} path={path} />
            ))}
          </div>
        ) : (
          <p className="empty-result">No changed files were detected.</p>
        )}
      </section>

      <section
        className="result-section"
        aria-labelledby="affected-changed-title"
      >
        <div className="result-section-heading">
          <div>
            <h3 id="affected-changed-title">Affected &amp; Changed</h3>
            <p className="muted">
              Related artifacts that were also included in the change.
            </p>
          </div>
        </div>

        {report.affected_and_changed.length > 0 ? (
          <div className="artifact-list">
            {report.affected_and_changed.map((artifact) => (
              <ArtifactCard
                key={artifact.path}
                artifact={artifact}
                variant="changed"
              />
            ))}
          </div>
        ) : (
          <p className="empty-result">
            No related artifacts were also changed.
          </p>
        )}
      </section>

            <section
        className={`result-section missing-section ${
          report.potentially_missing.length > 0 ? 'has-missing-artifacts' : ''
        }`}
        aria-labelledby="potentially-missing-title"
      >
        <div className="result-section-heading">
          <div>
            <h3 id="potentially-missing-title">Potentially Missing</h3>
            <p className="muted">
              Related artifacts not included in the detected change.
            </p>
          </div>
        </div>

        {report.potentially_missing.length > 0 ? (
          <div className="artifact-list">
            {report.potentially_missing.map((artifact) => (
              <ArtifactCard
                key={artifact.path}
                artifact={artifact}
                variant="missing"
              />
            ))}
          </div>
        ) : (
          <div className="empty-result complete-empty">
            <span aria-hidden="true">✓</span>
            <span>No potentially missing related artifacts were detected.</span>
          </div>
        )}
      </section>

      <section
        className="result-section"
        aria-labelledby="validation-title"
      >
        <div className="result-section-heading">
          <div>
            <h3 id="validation-title">Recommended Validation</h3>
            <p className="muted">
              Guidance based on the relationships discovered by the analysis.
            </p>
          </div>
        </div>

        {report.validation_recommendations.length > 0 ? (
          <ul className="recommendation-list">
            {report.validation_recommendations.map((recommendation) => (
              <li key={recommendation}>
                <span aria-hidden="true">□</span>
                <span>{recommendation}</span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="empty-result">
            No additional validation recommendations were returned.
          </p>
        )}
      </section>
    </section>
  )
}
