export function RiskBadge({ level, score }) {
  const labels = {
    low: 'Низкий риск',
    medium: 'Средний риск',
    high: 'Высокий риск',
    unknown: 'Недостаточно данных',
  };

  return (
    <div className={`riskBadge riskBadge--${level || 'unknown'}`}>
      <span>{labels[level] || labels.unknown}</span>
      <strong>{typeof score === 'number' ? `${score}%` : '—'}</strong>
    </div>
  );
}
