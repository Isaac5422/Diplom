import { useEffect, useRef, useState } from 'react';
import { api } from '../api/client.js';
import { RiskBadge } from '../components/RiskBadge.jsx';
import { FactorCard } from '../components/FactorCard.jsx';

const FORM_DEFAULTS = {
  full_name: '',
  email: '',
  target_position: '',
  level: 'Junior',
  declared_total_months: 0,
  resume_text: '',
};

export function Dashboard() {
  const [candidates, setCandidates] = useState([]);
  const [selectedCandidate, setSelectedCandidate] = useState(null);
  const [experiences, setExperiences] = useState([]);
  const [profiles, setProfiles] = useState([]);
  const [report, setReport] = useState(null);
  const [error, setError] = useState('');
  const [notification, setNotification] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [isRunningCheck, setIsRunningCheck] = useState(false);
  const [filterRisk, setFilterRisk] = useState(null);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [showUploadForm, setShowUploadForm] = useState(false);
  const [uploadResult, setUploadResult] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  const [createFormData, setCreateFormData] = useState(FORM_DEFAULTS);
  const [deletingId, setDeletingId] = useState(null);
  const notifTimer = useRef(null);

  function showNotification(msg) {
    setNotification(msg);
    clearTimeout(notifTimer.current);
    notifTimer.current = setTimeout(() => setNotification(''), 3000);
  }

  // Единая функция загрузки (заменяет loadCandidates + loadFilteredCandidates)
  async function loadCandidates(riskType = null) {
    try {
      setIsLoading(true);
      setError('');
      const data = riskType
        ? await api.getFilteredCandidates(riskType)
        : await api.getCandidates();
      const list = Array.isArray(data) ? data : [];
      setCandidates(list);
      if (list.length > 0 && !selectedCandidate) {
        setSelectedCandidate(list[0]);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  }

  async function selectCandidate(candidate) {
    try {
      setError('');
      setSelectedCandidate(candidate);
      setReport(null);
      const [expData, profileData] = await Promise.all([
        api.getExperiences(candidate.id),
        api.getProfiles(candidate.id),
      ]);
      setExperiences(Array.isArray(expData) ? expData : []);
      setProfiles(Array.isArray(profileData) ? profileData : []);
    } catch (err) {
      setExperiences([]);
      setProfiles([]);
      setError(err.message);
    }
  }

  async function runCheck() {
    if (!selectedCandidate) return;
    try {
      setError('');
      setIsRunningCheck(true);
      const data = await api.runCheck(selectedCandidate.id);
      setReport(data);
      await loadCandidates(filterRisk);
      showNotification('Проверка завершена');
    } catch (err) {
      setError(err.message);
    } finally {
      setIsRunningCheck(false);
    }
  }

  async function handleCreateCandidate(e) {
    e.preventDefault();
    const name = createFormData.full_name;
    try {
      setError('');
      await api.createCandidate(createFormData);
      setCreateFormData(FORM_DEFAULTS);
      setShowCreateForm(false);
      await loadCandidates(filterRisk);
      showNotification(`Кандидат «${name}» добавлен`);
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleDeleteCandidate(candidateId, candidateName) {
    if (!window.confirm(`Удалить кандидата «${candidateName}»?\nЭто действие нельзя отменить.`)) return;
    try {
      setError('');
      setDeletingId(candidateId);
      await api.deleteCandidate(candidateId);
      if (selectedCandidate?.id === candidateId) {
        setSelectedCandidate(null);
        setReport(null);
        setExperiences([]);
        setProfiles([]);
      }
      await loadCandidates(filterRisk);
      showNotification(`Кандидат «${candidateName}» удалён`);
    } catch (err) {
      setError(err.message);
    } finally {
      setDeletingId(null);
    }
  }

  function handleFilterChange(type) {
    setFilterRisk(type);
    loadCandidates(type);
  }

  function handleExportCsv(riskType) {
    const base = import.meta.env.VITE_API_URL || 'http://localhost:8000';
    window.location.href = `${base}/api/candidates/export/csv${riskType ? `?risk_type=${riskType}` : ''}`;
  }

  async function handleImportCsv(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      setIsUploading(true);
      setError('');
      const result = await api.importCandidatesCsv(file);
      setUploadResult(result);
      e.target.value = '';
      setTimeout(() => loadCandidates(filterRisk), 500);
    } catch (err) {
      setError(err.message);
      e.target.value = '';
    } finally {
      setIsUploading(false);
    }
  }

  function updateForm(field, value) {
    setCreateFormData((prev) => ({ ...prev, [field]: value }));
  }

  useEffect(() => {
    loadCandidates();
  }, []);

  useEffect(() => {
    if (selectedCandidate) {
      selectCandidate(selectedCandidate);
    }
  }, [selectedCandidate?.id]);

  const formatScore = (score) =>
    score !== null && score !== undefined ? Math.round(score) : null;

  const isHighRisk = (score) =>
    score !== null && score !== undefined && score > 50;

  return (
    <main className="layout">
      {notification && (
        <div className="notification" role="status">
          {notification}
        </div>
      )}

      <section className="hero">
        <div>
          <p className="eyebrow">ВКР · Resume Trust Analyzer</p>
          <h1>Система выявления признаков сфальсифицированного опыта в IT-резюме</h1>
          <p>
            Прототип собирает данные кандидата, анализирует опыт, цифровой след и формирует
            объяснимую риск-оценку для рекрутера.
          </p>
        </div>
        <button className="hero__btn" onClick={runCheck} disabled={!selectedCandidate || isRunningCheck}>
          {isRunningCheck ? 'Анализируем...' : 'Запустить проверку'}
        </button>
      </section>

      {error && (
        <div className="errorBox" role="alert">
          <span>{error}</span>
          <button className="errorBox__close" onClick={() => setError('')} aria-label="Закрыть">
            ✕
          </button>
        </div>
      )}

      <div className="grid">
        {/* ─── Левая колонка: список кандидатов ─── */}
        <section className="card">
          <h2>Кандидаты</h2>

          <button
            className={`btn btn--full ${showCreateForm ? 'btn--secondary' : 'btn--primary'}`}
            onClick={() => setShowCreateForm(!showCreateForm)}
          >
            {showCreateForm ? 'Закрыть форму' : '+ Добавить кандидата'}
          </button>

          {showCreateForm && (
            <form onSubmit={handleCreateCandidate} className="formSection">
              <div className="formGroup">
                <label className="formLabel">Имя и фамилия</label>
                <input
                  className="formInput"
                  type="text"
                  placeholder="Например: Иван Петров"
                  value={createFormData.full_name}
                  onChange={(e) => updateForm('full_name', e.target.value)}
                  required
                />
              </div>

              <div className="formGroup">
                <label className="formLabel">Email</label>
                <input
                  className="formInput"
                  type="email"
                  placeholder="например@mail.com"
                  value={createFormData.email}
                  onChange={(e) => updateForm('email', e.target.value)}
                />
              </div>

              <div className="formGroup">
                <label className="formLabel">Целевая позиция</label>
                <input
                  className="formInput"
                  type="text"
                  placeholder="Например: Senior Backend Developer"
                  value={createFormData.target_position}
                  onChange={(e) => updateForm('target_position', e.target.value)}
                  required
                />
                <span className="formHint">Будет проверяться соответствие опыта заявленной позиции</span>
              </div>

              <div className="formGroup">
                <label className="formLabel">Уровень квалификации</label>
                <select
                  className="formInput"
                  value={createFormData.level}
                  onChange={(e) => updateForm('level', e.target.value)}
                >
                  <option value="Junior">Junior (0–2 года)</option>
                  <option value="Middle">Middle (2–5 лет)</option>
                  <option value="Senior">Senior (5+ лет)</option>
                </select>
              </div>

              <div className="formGroup">
                <label className="formLabel">Заявленный стаж в IT</label>
                <div className="formRow">
                  <input
                    className="formInput formInput--narrow"
                    type="number"
                    value={createFormData.declared_total_months}
                    onChange={(e) =>
                      updateForm('declared_total_months', Math.max(0, parseInt(e.target.value) || 0))
                    }
                    min="0"
                    max="600"
                  />
                  <span className="formHint">
                    месяцев ≈ {Math.round(createFormData.declared_total_months / 12)} лет
                  </span>
                </div>
              </div>

              <div className="formGroup">
                <label className="formLabel">Текст резюме</label>
                <textarea
                  className="formInput formInput--textarea"
                  placeholder="Вставьте текст резюме кандидата (опыт, технологии, проекты...)"
                  value={createFormData.resume_text}
                  onChange={(e) => updateForm('resume_text', e.target.value)}
                />
              </div>

              <button type="submit" className="btn btn--primary btn--full">
                Добавить кандидата
              </button>
            </form>
          )}

          <button
            className={`btn btn--full ${showUploadForm ? 'btn--secondary' : 'btn--ghost'}`}
            onClick={() => {
              setShowUploadForm(!showUploadForm);
              setUploadResult(null);
            }}
          >
            {showUploadForm ? 'Закрыть загрузку' : 'Загрузить список CSV'}
          </button>

          {showUploadForm && (
            <div className="uploadArea">
              <p className="formHint">
                Колонки: <code>full_name, email, target_position, level, declared_total_months, resume_text</code>
              </p>
              <input
                className="formInput"
                type="file"
                accept=".csv"
                onChange={handleImportCsv}
                disabled={isUploading}
              />
              {isUploading && <p className="muted">Загрузка...</p>}
            </div>
          )}

          {uploadResult && (
            <div className="uploadResult">
              <p>
                Загружено: <strong>{uploadResult.created_count}</strong>
                {uploadResult.errors_count > 0 && ` · Ошибок: ${uploadResult.errors_count}`}
              </p>
              {uploadResult.errors_count > 0 && (
                <details>
                  <summary className="formHint">Показать ошибки</summary>
                  <div className="uploadResult__errors">
                    {uploadResult.errors.map((err, idx) => (
                      <p key={idx} className="uploadResult__error">
                        {err}
                      </p>
                    ))}
                  </div>
                </details>
              )}
              <button className="btn btn--secondary btn--sm" onClick={() => setUploadResult(null)}>
                Закрыть
              </button>
            </div>
          )}

          {/* Фильтрация */}
          <div className="filterBar">
            <button
              className={`btn btn--sm ${filterRisk === null ? 'btn--primary' : 'btn--ghost'}`}
              onClick={() => handleFilterChange(null)}
            >
              Все ({candidates.length})
            </button>
            <button
              className={`btn btn--sm ${filterRisk === 'high' ? 'btn--danger' : 'btn--ghost'}`}
              onClick={() => handleFilterChange('high')}
            >
              Высокий риск
            </button>
            <button
              className={`btn btn--sm ${filterRisk === 'low' ? 'btn--success' : 'btn--ghost'}`}
              onClick={() => handleFilterChange('low')}
            >
              Низкий риск
            </button>
          </div>

          {/* Экспорт */}
          <div className="exportBar">
            <button className="btn btn--ghost btn--sm" onClick={() => handleExportCsv()}>
              Экспорт всех
            </button>
            <button className="btn btn--danger btn--sm" onClick={() => handleExportCsv('high')}>
              Высокий риск
            </button>
            <button className="btn btn--success btn--sm" onClick={() => handleExportCsv('low')}>
              Низкий риск
            </button>
          </div>

          {/* Список кандидатов */}
          <div className="candidateList">
            {isLoading && <p className="muted">Загрузка кандидатов...</p>}
            {!isLoading && candidates.length === 0 && (
              <div className="emptyState">
                <p>Кандидаты не найдены.</p>
                <p className="muted">Убедитесь, что backend запущен.</p>
              </div>
            )}
            {candidates.map((candidate) => {
              const score = formatScore(candidate.last_risk_score);
              const highRisk = isHighRisk(candidate.last_risk_score);
              return (
                <div
                  key={candidate.id}
                  className={`candidateItem ${selectedCandidate?.id === candidate.id ? 'candidateItem--active' : ''}`}
                >
                  <button
                    className="candidateItem__main"
                    onClick={() => selectCandidate(candidate)}
                  >
                    <strong>{candidate.full_name}</strong>
                    <span>{candidate.target_position} · {candidate.level}</span>
                    <small>Опыт: {candidate.declared_total_months} мес.</small>
                    {score !== null && (
                      <small className={highRisk ? 'riskText--high' : 'riskText--low'}>
                        Риск: {score}%
                      </small>
                    )}
                  </button>
                  <button
                    className="candidateItem__delete"
                    onClick={() => handleDeleteCandidate(candidate.id, candidate.full_name)}
                    disabled={deletingId === candidate.id}
                    title="Удалить кандидата"
                    aria-label={`Удалить ${candidate.full_name}`}
                  >
                    {deletingId === candidate.id ? '…' : '✕'}
                  </button>
                </div>
              );
            })}
          </div>
        </section>

        {/* ─── Правая колонка: детали кандидата ─── */}
        <section className="card card--wide">
          {selectedCandidate ? (
            <>
              <div className="sectionHeader">
                <div>
                  <h2>{selectedCandidate.full_name}</h2>
                  <p>{selectedCandidate.target_position} · {selectedCandidate.level}</p>
                </div>
                {report && <RiskBadge level={report.risk_level} score={report.risk_score} />}
              </div>

              <div className="infoGrid">
                <div>
                  <h3>Резюме</h3>
                  <p>{selectedCandidate.resume_text || 'Текст резюме не заполнен.'}</p>
                </div>
                <div>
                  <h3>Внешние профили</h3>
                  {profiles.length === 0 ? (
                    <p className="muted">Нет подключённых профилей.</p>
                  ) : (
                    profiles.map((profile) => (
                      <p key={profile.id}>
                        <strong>{profile.profile_type}</strong>:{' '}
                        <a href={profile.profile_url} target="_blank" rel="noopener noreferrer">
                          {profile.profile_url}
                        </a>
                      </p>
                    ))
                  )}
                </div>
              </div>

              <h3>Опыт работы</h3>
              {experiences.length === 0 ? (
                <p className="muted">Опыт работы не добавлен.</p>
              ) : (
                <div className="timeline">
                  {experiences.map((experience) => (
                    <article key={experience.id}>
                      <strong>{experience.position_name}</strong>
                      <span>{experience.company_name}</span>
                      <small>
                        {experience.started_at} — {experience.ended_at || 'по настоящее время'}
                      </small>
                      {experience.description && <p>{experience.description}</p>}
                    </article>
                  ))}
                </div>
              )}
            </>
          ) : (
            <div className="emptyState">
              <p>Выберите кандидата из списка слева.</p>
            </div>
          )}
        </section>
      </div>

      {/* ─── Отчёт проверки ─── */}
      {report && (
        <section className="card report">
          <div className="sectionHeader">
            <div>
              <h2>Отчёт проверки</h2>
              <p>{report.summary}</p>
            </div>
            <RiskBadge level={report.risk_level} score={report.risk_score} />
          </div>

          <div className="factorGrid">
            {report.factors.map((factor) => (
              <FactorCard key={factor.code} factor={factor} />
            ))}
          </div>
        </section>
      )}
    </main>
  );
}
