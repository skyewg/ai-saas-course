import React, { useEffect, useRef, useState } from 'react';

const initialState = { status: 'loading', data: null };

function Icon({ name, size = 20 }) {
  const paths = {
    overview: <><rect x="3" y="3" width="7" height="7" rx="1.5" /><rect x="14" y="3" width="7" height="7" rx="1.5" /><rect x="3" y="14" width="7" height="7" rx="1.5" /><rect x="14" y="14" width="7" height="7" rx="1.5" /></>,
    wallet: <><path d="M4 7.5A2.5 2.5 0 0 1 6.5 5H19v14H6.5A2.5 2.5 0 0 1 4 16.5z" /><path d="M4 8h15M15 12h5v3h-5a1.5 1.5 0 0 1 0-3z" /></>,
    down: <><path d="M12 4v15M6.5 13.5 12 19l5.5-5.5" /></>,
    up: <><path d="M12 20V5M6.5 10.5 12 5l5.5 5.5" /></>,
    refresh: <><path d="M20 11a8 8 0 0 0-14-5L4 8" /><path d="M4 4v4h4M4 13a8 8 0 0 0 14 5l2-2" /><path d="M20 20v-4h-4" /></>,
    list: <><path d="M9 6h11M9 12h11M9 18h11" /><path d="M4 6h.01M4 12h.01M4 18h.01" /></>,
    trash: <><path d="M4 7h16M10 4h4M6.5 7l.8 12a1.5 1.5 0 0 0 1.5 1.4h6.4a1.5 1.5 0 0 0 1.5-1.4L17.5 7M10 11v5M14 11v5" /></>,
    edit: <><path d="M4 20l4.2-.8L19.5 7.9a2.1 2.1 0 0 0-3-3L5.2 16.2 4 20zM14.8 6.6l2.6 2.6" /></>,
  };
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{paths[name]}</svg>;
}

async function readJson(path, signal, validate) {
  const response = await fetch(path, { signal, headers: { Accept: 'application/json' } });
  if (!response.ok) throw new Error('Сервер тимчасово недоступний');
  const data = await response.json();
  if (!validate(data)) throw new Error('Сервер повернув невірний формат даних');
  return data;
}

const isAmount = (value) => typeof value === 'string' && /^-?\d+(?:\.\d{1,2})?$/.test(value);
const validSummary = (data) => data && typeof data === 'object' &&
  ['total_incom', 'total_expense', 'balance'].every((key) => isAmount(data[key]));
const validTransactions = (data) => Array.isArray(data) && data.every((item) =>
  item && typeof item === 'object' && item.id != null && item.user_id != null &&
  (item.type === 'income' || item.type === 'expense') && typeof item.category === 'string' &&
  isAmount(item.amount) && typeof item.created_at === 'string');

// Format decimal strings directly, keeping the exact amount returned by the API.
function formatAmount(value) {
  const [whole, fraction = '00'] = String(value).split('.');
  const grouped = whole.replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
  return `${grouped},${fraction.padEnd(2, '0')}`;
}

function formatDate(value) {
  const date = /^\d{4}-\d{2}-\d{2}$/.test(value)
    ? new Date(`${value}T12:00:00`)
    : new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  const options = { day: 'numeric', month: 'short', year: 'numeric' };
  if (value.includes('T') && !/^\d{4}-\d{2}-\d{2}$/.test(value)) Object.assign(options, { hour: '2-digit', minute: '2-digit' });
  return new Intl.DateTimeFormat('uk-UA', options).format(date);
}

function ErrorState({ onRetry }) {
  return <div className="state-message error-state" role="alert"><span className="error-icon">!</span><div><strong>Не вдалося завантажити дані</strong><p>Перевірте, чи запущено API та чи доступна база даних.</p><button className="text-button" onClick={onRetry}>Спробувати ще раз</button></div></div>;
}

function Metric({ icon, title, value, tone, description }) {
  return <article className={`metric metric-${tone}`}><div className="metric-top"><span className="metric-title">{title}</span><span className={`metric-icon icon-${tone}`}><Icon name={icon} size={19} /></span></div><div className="metric-amount">{formatAmount(value)}</div><div className="metric-description">{description}</div></article>;
}

export function Summary({ state, onRetry }) {
  if (state.status === 'loading') return <div className="metric-grid" aria-live="polite" aria-busy="true">{[1, 2, 3].map((n) => <div className="metric skeleton-card" key={n}><span className="skeleton short" /><span className="skeleton large" /><span className="skeleton medium" /></div>)}<span className="sr-only">Завантажуємо підсумок</span></div>;
  if (state.status === 'error') return <ErrorState onRetry={onRetry} />;
  return <div className="metric-grid"><Metric icon="wallet" title="Загальний баланс" value={state.data.balance} tone="balance" description="Доходи мінус витрати" /><Metric icon="up" title="Усього доходів" value={state.data.total_incom} tone="income" description="За весь час" /><Metric icon="down" title="Усього витрат" value={state.data.total_expense} tone="expense" description="За весь час" /></div>;
}

function validateFields(amount, category) {
  if (!/^[0-9]{1,10}(?:\.[0-9]{1,2})?$/.test(amount)) return 'Вкажіть невід’ємну суму з не більше ніж двома знаками після коми.';
  if (!category || category.length > 100 || !/\p{L}/u.test(category) || !/^[\p{L}\p{M} '’ʼ-]+$/u.test(category)) return 'Категорія має містити лише літери, пробіли, дефіс або апостроф.';
  return '';
}

export function Transactions({ state, onRetry, onDelete, onUpdated }) {
  const [editing, setEditing] = useState(null);
  const [values, setValues] = useState(null);
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  const savingRef = useRef(false);

  useEffect(() => {
    if (state.status === 'success' && editing && !state.data.some((item) => item.id === editing.id && item.type === editing.type)) {
      setEditing(null);
      setError('');
    }
  }, [state, editing]);

  function startEdit(item) {
    setEditing(item);
    setValues({ type: item.type, amount: item.amount, category: item.category, date: item.date || '' });
    setError('');
  }

  function changeValue(field, value) {
    setValues((previous) => ({ ...previous, [field]: value }));
    setError('');
  }

  async function saveEdit() {
    if (!editing || savingRef.current) return;
    const amount = values.amount.trim().replace(',', '.');
    const category = values.category.trim();
    const validationError = validateFields(amount, category);
    if (validationError) { setError(validationError); return; }
    savingRef.current = true;
    setSaving(true);
    setError('');
    try {
      const response = await fetch(`/api/transactions/${encodeURIComponent(editing.id)}?type=${encodeURIComponent(editing.type)}`, {
        method: 'PUT', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ type: values.type, amount, category, date: values.date || localDateToday() }),
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || 'Не вдалося оновити транзакцію.');
      setEditing(null);
      onUpdated();
    } catch (error) {
      setError(error instanceof TypeError ? 'Не вдалося з’єднатися із сервером.' : error.message);
    } finally {
      savingRef.current = false;
      setSaving(false);
    }
  }

  if (state.status === 'loading') return <div className="state-message loading-state" role="status"><span className="spinner" /> Завантажуємо транзакції…</div>;
  if (state.status === 'error') return <ErrorState onRetry={onRetry} />;
  if (!state.data.length) return <div className="empty-state"><span className="empty-icon"><Icon name="list" size={24} /></span><strong>Транзакцій поки немає</strong><p>Додайте першу транзакцію через форму або витрату через Telegram-бота.</p></div>;
  return <div className="table-scroll"><table><thead><tr><th>Назва категорії</th><th>Дата</th><th>ID користувача</th><th className="align-right">Сума</th><th><span className="sr-only">Дії</span></th></tr></thead><tbody>{state.data.map((item) => {
    const isEditing = editing && editing.id === item.id && editing.type === item.type;
    return <React.Fragment key={`${item.type}-${item.id}`}><tr>
      <td>{isEditing ? <div className="inline-category"><select aria-label="Тип операції" value={values.type} disabled={saving} onChange={(event) => changeValue('type', event.target.value)}><option value="expense">Витрата</option><option value="income">Дохід</option></select><input aria-label="Категорія" type="text" maxLength="100" value={values.category} disabled={saving} onChange={(event) => changeValue('category', event.target.value)} /></div> : <div className="category-cell"><span className="category-avatar"><Icon name={item.type === 'income' ? 'down' : 'up'} size={16} /></span><span><strong>{item.category}</strong><small>{item.type === 'income' ? 'Дохід' : 'Витрата'}</small></span></div>}</td>
      <td className="muted">{isEditing ? <input className="inline-input" aria-label="Дата операції" type="date" value={values.date} disabled={saving} onChange={(event) => changeValue('date', event.target.value)} /> : formatDate(item.date || item.created_at)}</td>
      <td className="muted">#{item.user_id}</td>
      <td className="align-right">{isEditing ? <input className="inline-input inline-amount" aria-label="Сума" type="number" min="0" max="9999999999.99" step="0.01" value={values.amount} disabled={saving} onChange={(event) => changeValue('amount', event.target.value)} /> : <strong className="expense-amount">{item.type === 'income' ? '+' : '−'}{formatAmount(item.amount)}</strong>}</td>
      <td className="delete-cell"><div className="row-actions">{isEditing ? <><button type="button" className="inline-save-button" onClick={saveEdit} disabled={saving}>{saving ? 'Зберігаємо…' : 'Зберегти'}</button><button type="button" className="inline-cancel-button" onClick={() => { setEditing(null); setError(''); }} disabled={saving}>Скасувати</button></> : <><button type="button" className="edit-icon-button" aria-label={`Редагувати ${item.type === 'income' ? 'дохід' : 'витрату'}: ${item.category}, ${formatAmount(item.amount)}`} title="Редагувати транзакцію" disabled={Boolean(editing)} onClick={() => startEdit(item)}><Icon name="edit" size={18} /></button><button type="button" className="delete-icon-button" aria-label={`Видалити ${item.type === 'income' ? 'дохід' : 'витрату'}: ${item.category}, ${formatAmount(item.amount)}`} title="Видалити транзакцію" disabled={Boolean(editing)} onClick={() => onDelete(item)}><Icon name="trash" size={18} /></button></>}</div></td>
    </tr>{isEditing && error && <tr className="inline-error-row"><td colSpan="5"><p role="alert">{error}</p></td></tr>}</React.Fragment>;
  })}</tbody></table></div>;
}

function DeleteDialog({ transaction, deleting, error, onCancel, onConfirm }) {
  const dialogRef = useRef(null);

  useEffect(() => {
    const dialog = dialogRef.current;
    dialog.showModal();
    return () => { if (dialog.open) dialog.close(); };
  }, []);

  function handleCancel(event) {
    event.preventDefault();
    if (!deleting) onCancel();
  }

  return <dialog ref={dialogRef} className="delete-dialog" aria-labelledby="delete-title" aria-describedby="delete-description" onCancel={handleCancel}>
    <div className="delete-dialog-icon"><Icon name="trash" size={22} /></div>
    <h2 id="delete-title">Видалити транзакцію?</h2>
    <p id="delete-description">Ви збираєтесь видалити {transaction.type === 'income' ? 'дохід' : 'витрату'} <strong>«{transaction.category}» на суму {formatAmount(transaction.amount)}</strong> від {formatDate(transaction.date || transaction.created_at)}. Цю дію не можна скасувати.</p>
    {error && <p role="alert" className="delete-error">{error}</p>}
    <div className="delete-dialog-actions"><button type="button" className="cancel-delete-button" onClick={onCancel} disabled={deleting} autoFocus>Скасувати</button><button type="button" className="confirm-delete-button" onClick={onConfirm} disabled={deleting}>{deleting ? 'Видаляємо…' : 'Підтвердити'}</button></div>
  </dialog>;
}

function localDateToday() {
  const today = new Date();
  const year = today.getFullYear();
  const month = String(today.getMonth() + 1).padStart(2, '0');
  const day = String(today.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

export function TransactionForm({ onSaved }) {
  const [date, setDate] = useState('');
  const [notice, setNotice] = useState('');
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const values = new FormData(form);
    const amount = String(values.get('amount')).trim().replace(',', '.');
    const category = String(values.get('category')).trim();
    const validationError = validateFields(amount, category);
    if (validationError) { setError(validationError); return; }
    setError('');
    setNotice('');
    setSaving(true);
    try {
      const response = await fetch('/api/transaction', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ type: values.get('type'), amount, category, date: date || localDateToday() }),
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || 'Не вдалося зберегти транзакцію.');
      form.reset();
      setDate('');
      setNotice('Транзакцію збережено.');
      onSaved();
    } catch (error) {
      setError(error.message || 'Не вдалося зберегти транзакцію.');
    } finally {
      setSaving(false);
    }
  }

  return <section className="transaction-form-section" aria-labelledby="new-transaction-heading">
    <div className="section-heading"><div><h2 id="new-transaction-heading">Нова транзакція</h2><p>Вкажіть дані доходу або витрати</p></div></div>
    <form className="transaction-form" onSubmit={handleSubmit} onInput={() => { setNotice(''); setError(''); }}>
      <div className="form-grid">
        <div className="form-field"><label htmlFor="transaction-type">Тип операції</label><select id="transaction-type" name="type" defaultValue="expense"><option value="expense">Витрата</option><option value="income">Дохід</option></select></div>
        <div className="form-field"><label htmlFor="transaction-amount">Сума</label><input id="transaction-amount" name="amount" type="number" min="0" max="9999999999.99" step="0.01" placeholder="0,00" required /></div>
        <div className="form-field"><label htmlFor="transaction-category">Категорія</label><input id="transaction-category" name="category" type="text" maxLength="100" placeholder="Наприклад, кава" required /></div>
        <div className="form-field"><label htmlFor="transaction-date">Дата <span>(необов’язково)</span></label><input id="transaction-date" name="date" type="date" value={date} onChange={(event) => setDate(event.target.value)} /><small>Якщо не обрати, використовується поточна дата.</small></div>
      </div>
      <div className="form-actions"><button type="submit" className="save-button" disabled={saving}>{saving ? 'Зберігаємо…' : 'Зберегти'}</button>{notice && <p role="status" className="form-notice">{notice}</p>}{error && <p role="alert" className="form-error">{error}</p>}</div>
    </form>
  </section>;
}

export default function App() {
  const [summary, setSummary] = useState(initialState);
  const [transactions, setTransactions] = useState(initialState);
  const [requestId, setRequestId] = useState(0);
  const [selectedTransaction, setSelectedTransaction] = useState(null);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState('');
  const deletingRef = useRef(false);
  const refresh = () => setRequestId((value) => value + 1);

  function openDeleteDialog(transaction) {
    setDeleteError('');
    setSelectedTransaction(transaction);
  }

  async function confirmDelete() {
    if (!selectedTransaction || deletingRef.current) return;
    deletingRef.current = true;
    setDeleting(true);
    setDeleteError('');
    try {
      const { id, type } = selectedTransaction;
      const response = await fetch(`/api/transactions/${encodeURIComponent(id)}?type=${encodeURIComponent(type)}`, { method: 'DELETE' });
      if (response.status === 404) throw new Error('Транзакцію вже не знайдено. Оновіть дані.');
      if (!response.ok) throw new Error('Не вдалося видалити транзакцію. Спробуйте ще раз.');
      setSelectedTransaction(null);
      refresh();
    } catch (error) {
      setDeleteError(error instanceof TypeError ? 'Не вдалося з’єднатися із сервером.' : error.message);
    } finally {
      deletingRef.current = false;
      setDeleting(false);
    }
  }

  useEffect(() => {
    const controller = new AbortController();
    setSummary(initialState);
    setTransactions(initialState);
    const load = (path, validate, setState) => {
      readJson(path, controller.signal, validate)
        .then((data) => setState({ status: 'success', data }))
        .catch((error) => { if (error.name !== 'AbortError') setState({ status: 'error', data: null }); });
    };
    load('/api/summary', validSummary, setSummary);
    load('/api/transaction', validTransactions, setTransactions);
    return () => controller.abort();
  }, [requestId]);

  const count = transactions.status === 'success' ? transactions.data.length : null;
  return <div className="app-shell">
    <aside className="sidebar"><a className="brand" href="/" aria-label="Finansovik, головна"><span className="brand-mark"><span /></span><span>finansovik<span className="brand-dot">.</span></span></a><div className="side-label">МЕНЮ</div><div className="side-current" aria-current="page"><Icon name="overview" size={19} /> Огляд</div><div className="side-bottom"><span className="side-bottom-icon"><Icon name="wallet" size={20} /></span><div><strong>Ваша фінансова панель</strong><p>Усі записи в одному місці.</p></div></div></aside>
    <div className="main-area"><header className="topbar"><div className="breadcrumb"><span>Finansovik</span><span className="breadcrumb-separator">/</span><strong>Огляд</strong></div><span className="topbar-caption">ФІНАНСОВА ПАНЕЛЬ</span></header>
      <main className="content"><div className="page-heading"><div><div className="eyebrow"><span /> ФІНАНСИ ПІД КОНТРОЛЕМ</div><h1>Огляд фінансів<span>.</span></h1><p>Доходи, витрати та всі ваші транзакції в одному місці.</p></div><button className="refresh-button" onClick={refresh}><Icon name="refresh" size={17} /> Оновити дані</button></div>
        <section aria-labelledby="summary-heading"><div className="section-heading"><div><h2 id="summary-heading">Підсумок</h2><p>Загальна картина за весь час</p></div><span className="section-period">ЗА ВЕСЬ ЧАС</span></div><Summary state={summary} onRetry={refresh} /></section>
        <TransactionForm onSaved={refresh} />
        <section className="transactions-section" aria-labelledby="transactions-heading"><div className="section-heading"><div><h2 id="transactions-heading">Історія транзакцій</h2><p>Деталі доходів і витрат</p></div>{count !== null && <span className="count-badge">{count} записів</span>}</div><div className="table-card"><div className="table-card-heading"><div><span className="table-card-icon"><Icon name="list" size={18} /></span><div><strong>Усі транзакції</strong><small>Найновіші спочатку</small></div></div><span className="table-label">ІСТОРІЯ</span></div><Transactions state={transactions} onRetry={refresh} onDelete={openDeleteDialog} onUpdated={refresh} /></div></section>
        {selectedTransaction && <DeleteDialog transaction={selectedTransaction} deleting={deleting} error={deleteError} onCancel={() => setSelectedTransaction(null)} onConfirm={confirmDelete} />}
        <footer className="page-footer"><span>© Finansovik</span><span>Дані з вашої бази · Локальний перегляд</span></footer>
      </main>
    </div>
  </div>;
}
