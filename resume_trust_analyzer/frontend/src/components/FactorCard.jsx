export function FactorCard({ factor }) {
  return (
    <article className="factorCard">
      <div className="factorCard__header">
        <div>
          <span className="factorCard__code">{factor.code}</span>
          <h4>{factor.title}</h4>
        </div>
        <strong>{factor.points} баллов</strong>
      </div>

      <p>{factor.explanation}</p>

      <div className="recommendation">
        <span>Рекомендация</span>
        <p>{factor.recommendation}</p>
      </div>
    </article>
  );
}
