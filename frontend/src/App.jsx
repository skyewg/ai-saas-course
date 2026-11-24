import React, { useEffect, useRef, useState } from 'react';

const emptyLoad = { status: 'loading', data: null };
const filters = [['all', 'Усі транзакції'], ['income', 'Усі доходи'], ['expense', 'Усі витрати']];

function SymbolIcon({ type }) {
  const icons = {
    edit: <><path d="M4 20l4-.8L19 8a2 2 0 0 0-3-3L5 16z" /><path d="m14 7 3 3" /></>,
    trash: <><path d="M4 7h16M10 4h4M6 7l1 12h10l1-12M10 11v5M14 11v5" /></>,
    reload: <><path d="M20 11a8 8 0 0 0-14-5L4 8M4 4v4h4M4 13a8 8 0 0 0 14 5l2-2M20 20v-4h-4" /></>,
  };
  return <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{icons[type]}</svg>;
}

function money(value) {
  const [whole, fraction = '00'] = String(value).split('.');
  return `${whole.replace(/\B(?=(\d{3})+(?!\d))/g, ' ')},${fraction.padEnd(2, '0')}`;
}

function today() {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
}

function displayDate(value) {
  const parsed = new Date(value.length === 10 ? `${value}T12:00:00` : value);
  return Number.isNaN(parsed.getTime()) ? value : new Intl.DateTimeFormat('uk-UA', { day: 'numeric', month: 'short', year: 'numeric' }).format(parsed);
}

function fieldError(amount, category) {
  if (!/^[0-9]{1,10}(?:\.[0-9]{1,2})?$/.test(amount)) return 'Вкажіть невід’ємну суму з не більше ніж двома знаками після коми.';
  if (!category || category.length > 100 || !/\p{L}/u.test(category) || !/^[\p{L}\p{M} '’ʼ-]+$/u.test(category)) return 'Категорія має містити лише літери, пробіли, дефіс або апостроф.';
  return '';
}

async function request(path, options) {
  const response = await fetch(path, options);
  if (response.status === 204) return null;
  let data;
  try { data = await response.json(); }
  catch { throw new Error('Не вдалося отримати відповідь сервера.'); }
  if (!response.ok) throw new Error(data.error || 'Не вдалося виконати запит.');
  return data;
}

function LoadError({ onRetry }) {
  return <div className="load-message error" role="alert"><strong>Не вдалося завантажити дані</strong><p>Перевірте, чи запущені API та база даних.</p><button type="button" className="link-button" onClick={onRetry}>Спробувати ще раз</button></div>;
}

function Summary({ state, reload }) {
  if (state.status === 'loading') return <div className="summary-grid" role="status"><div className="summary-card skeleton">Завантажуємо підсумок…</div></div>;
  if (state.status === 'error') return <LoadError onRetry={reload} />;
  return <div className="summary-grid">
    {[['Загальний баланс', state.data.balance, 'balance', '◈', 'Доходи мінус витрати'], ['Усього доходів', state.data.total_incom, 'income', '↑', 'За весь час'], ['Усього витрат', state.data.total_expense, 'expense', '↓', 'За весь час']].map(([title, amount, type, icon, note]) =>
      <article className={`summary-card ${type}`} key={type}><div className="summary-top"><span>{title}</span><span className="summary-icon" aria-hidden="true">{icon}</span></div><strong>{money(amount)}</strong><small>{note}</small></article>)}
  </div>;
}

function TransactionForm({ onSaved }) {
  const [form, setForm] = useState({ type: 'expense', amount: '', category: '', date: '' });
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const inFlight = useRef(false);
  function change(field, value) { setForm((old) => ({ ...old, [field]: value })); setError(''); setMessage(''); }
  async function submit(event) {
    event.preventDefault();
    if (inFlight.current) return;
    const amount = form.amount.trim().replace(',', '.'); const category = form.category.trim();
    const invalid = fieldError(amount, category);
    if (invalid) { setError(invalid); return; }
    inFlight.current = true; setBusy(true); setError(''); setMessage('');
    try {
      await request('/api/transaction', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ...form, amount, category, date: form.date || today() }) });
      setForm({ type: 'expense', amount: '', category: '', date: '' }); setMessage('Транзакцію збережено.'); onSaved();
    } catch (error) { setError(error instanceof TypeError ? 'Не вдалося з’єднатися із сервером.' : error.message); }
    finally { inFlight.current = false; setBusy(false); }
  }
  return <section className="section"><div className="section-title"><div><h2>Нова транзакція</h2><p>Вкажіть дані доходу або витрати</p></div></div>
    <form className="panel entry-form" onSubmit={submit}>
      <div className="form-grid">
        <label>Тип операції<select value={form.type} onChange={(e) => change('type', e.target.value)}><option value="expense">Витрата</option><option value="income">Дохід</option></select></label>
        <label>Сума<input type="number" min="0" max="9999999999.99" step="0.01" placeholder="0,00" value={form.amount} onChange={(e) => change('amount', e.target.value)} required /></label>
        <label>Категорія<input type="text" maxLength="100" placeholder="Наприклад, кава" value={form.category} onChange={(e) => change('category', e.target.value)} required /></label>
        <label>Дата <span className="optional">(необов’язково)</span><input type="date" value={form.date} onChange={(e) => change('date', e.target.value)} /><small>Без вибору використаємо поточну дату.</small></label>
      </div>
      <div className="form-actions"><button type="submit" className="primary" disabled={busy}>{busy ? 'Зберігаємо…' : 'Зберегти'}</button>{message && <span role="status" className="success-text">{message}</span>}{error && <span role="alert" className="error-text">{error}</span>}</div>
    </form>
  </section>;
}

function DeleteDialog({ item, busy, error, onCancel, onConfirm }) {
  const ref = useRef(null);
  useEffect(() => { const dialog = ref.current; dialog.showModal(); return () => { if (dialog.open) dialog.close(); }; }, []);
  return <dialog ref={ref} className="modal" aria-labelledby="delete-title" aria-describedby="delete-desc" onCancel={(e) => { e.preventDefault(); if (!busy) onCancel(); }}>
    <span className="danger-mark"><SymbolIcon type="trash" /></span><h2 id="delete-title">Видалити транзакцію?</h2>
    <p id="delete-desc">Ви збираєтесь видалити {item.type === 'income' ? 'дохід' : 'витрату'} <strong>«{item.category}» на суму {money(item.amount)}</strong> від {displayDate(item.date || item.created_at)}. Цю дію не можна скасувати.</p>
    {error && <p role="alert" className="error-text">{error}</p>}
    <div className="modal-actions"><button type="button" className="secondary" onClick={onCancel} disabled={busy} autoFocus>Скасувати</button><button type="button" className="danger" onClick={onConfirm} disabled={busy}>{busy ? 'Видаляємо…' : 'Підтвердити'}</button></div>
  </dialog>;
}

function TransactionTable({ state, onRefresh }) {
  const [filter, setFilter] = useState('all');
  const [editing, setEditing] = useState(null);
  const [values, setValues] = useState(null);
  const [editError, setEditError] = useState('');
  const [saving, setSaving] = useState(false);
  const editLock = useRef(false);
  const [selected, setSelected] = useState(null);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState('');
  const deleteLock = useRef(false);

  useEffect(() => {
    if (state.status === 'success' && editing && !state.data.some((x) => x.id === editing.id && x.type === editing.type)) { setEditing(null); setEditError(''); }
  }, [state, editing]);
  function startEdit(item) { setEditing(item); setValues({ type: item.type, amount: item.amount, category: item.category, date: item.date || '' }); setEditError(''); }
  function change(field, value) { setValues((old) => ({ ...old, [field]: value })); setEditError(''); }
  async function saveEdit() {
    if (editLock.current || !editing) return;
    const amount = values.amount.trim().replace(',', '.'); const category = values.category.trim();
    const invalid = fieldError(amount, category); if (invalid) { setEditError(invalid); return; }
    editLock.current = true; setSaving(true); setEditError('');
    try {
      await request(`/api/transactions/${encodeURIComponent(editing.id)}?type=${encodeURIComponent(editing.type)}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ...values, amount, category, date: values.date || today() }) });
      setEditing(null); onRefresh();
    } catch (error) { setEditError(error instanceof TypeError ? 'Не вдалося з’єднатися із сервером.' : error.message); }
    finally { editLock.current = false; setSaving(false); }
  }
  async function confirmDelete() {
    if (!selected || deleteLock.current) return;
    deleteLock.current = true; setDeleting(true); setDeleteError('');
    try { await request(`/api/transactions/${encodeURIComponent(selected.id)}?type=${encodeURIComponent(selected.type)}`, { method: 'DELETE' }); setSelected(null); onRefresh(); }
    catch (error) { setDeleteError(error instanceof TypeError ? 'Не вдалося з’єднатися із сервером.' : error.message); }
    finally { deleteLock.current = false; setDeleting(false); }
  }
  const items = state.data || [];
  const visible = filter === 'all' ? items : items.filter((x) => x.type === filter);
  return <section className="section"><div className="section-title"><div><h2>Історія транзакцій</h2><p>Деталі доходів і витрат</p></div>{state.status === 'success' && <span className="count">Усього записів: {items.length}</span>}</div>
    <div className="panel table-panel"><div className="table-heading"><span className="list-icon" aria-hidden="true">☷</span><div><div className="filters" role="group" aria-label="Фільтр транзакцій" title={editing ? 'Завершіть редагування, щоб змінити фільтр' : undefined}>{filters.map(([id, label]) => <button type="button" key={id} aria-pressed={filter === id} disabled={!!editing} className={filter === id ? 'active' : ''} onClick={() => setFilter(id)}>{label}</button>)}</div><small>Найновіші спочатку</small></div></div>
      {state.status === 'loading' ? <div className="load-message" role="status">Завантажуємо транзакції…</div> : state.status === 'error' ? <LoadError onRetry={onRefresh} /> : !visible.length ? <div className="empty"><strong>{filter === 'income' ? 'Доходів поки немає' : filter === 'expense' ? 'Витрат поки немає' : 'Транзакцій поки немає'}</strong><p>Додайте транзакцію через форму або витрату через Telegram-бота.</p></div> :
        <div className="table-scroll"><table><thead><tr><th>Назва категорії</th><th>Дата</th><th>ID користувача</th><th className="number">Сума</th><th><span className="sr-only">Дії</span></th></tr></thead><tbody>{visible.map((item) => {
          const isEditing = editing && item.id === editing.id && item.type === editing.type;
          return <React.Fragment key={`${item.type}-${item.id}`}><tr>
            <td>{isEditing ? <div className="edit-category"><select aria-label="Тип операції" value={values.type} disabled={saving} onChange={(e) => change('type', e.target.value)}><option value="expense">Витрата</option><option value="income">Дохід</option></select><input aria-label="Категорія" value={values.category} maxLength="100" disabled={saving} onChange={(e) => change('category', e.target.value)} /></div> : <div className="category"><span className={`category-icon ${item.type}`}>{item.type === 'income' ? '↑' : '↓'}</span><div><strong>{item.category}</strong><small>{item.type === 'income' ? 'Дохід' : 'Витрата'}</small></div></div>}</td>
            <td>{isEditing ? <input className="edit-input" aria-label="Дата операції" type="date" value={values.date} disabled={saving} onChange={(e) => change('date', e.target.value)} /> : displayDate(item.date || item.created_at)}</td>
            <td>#{item.user_id}</td><td className="number">{isEditing ? <input className="edit-input edit-amount" aria-label="Сума" type="number" min="0" max="9999999999.99" step="0.01" value={values.amount} disabled={saving} onChange={(e) => change('amount', e.target.value)} /> : <strong>{item.type === 'income' ? '+' : '−'}{money(item.amount)}</strong>}</td>
            <td><div className="row-actions">{isEditing ? <><button type="button" className="primary small-button" disabled={saving} onClick={saveEdit}>{saving ? 'Зберігаємо…' : 'Зберегти'}</button><button type="button" className="secondary small-button" disabled={saving} onClick={() => { setEditing(null); setEditError(''); }}>Скасувати</button></> : <><button type="button" className="icon-button edit-button" title="Редагувати транзакцію" aria-label={`Редагувати ${item.category}`} disabled={!!editing} onClick={() => startEdit(item)}><SymbolIcon type="edit" /></button><button type="button" className="icon-button delete-button" title="Видалити транзакцію" aria-label={`Видалити ${item.category}`} disabled={!!editing} onClick={() => { setDeleteError(''); setSelected(item); }}><SymbolIcon type="trash" /></button></>}</div></td>
          </tr>{isEditing && editError && <tr><td colSpan="5"><p role="alert" className="error-text">{editError}</p></td></tr>}</React.Fragment>;
        })}</tbody></table></div>}
    </div>{selected && <DeleteDialog item={selected} busy={deleting} error={deleteError} onCancel={() => setSelected(null)} onConfirm={confirmDelete} />}
  </section>;
}

export default function App() {
  const [summary, setSummary] = useState(emptyLoad); const [transactions, setTransactions] = useState(emptyLoad); const [version, setVersion] = useState(0);
  const refresh = () => setVersion((old) => old + 1);
  useEffect(() => {
    const controller = new AbortController(); setSummary(emptyLoad); setTransactions(emptyLoad);
    function load(url, setState, valid) { request(url, { signal: controller.signal }).then((data) => { if (!valid(data)) throw new Error('Invalid data'); setState({ status: 'success', data }); }).catch((error) => { if (error.name !== 'AbortError') setState({ status: 'error', data: null }); }); }
    load('/api/summary', setSummary, (data) => data && ['total_incom', 'total_expense', 'balance'].every((key) => typeof data[key] === 'string'));
    load('/api/transaction', setTransactions, (data) => Array.isArray(data) && data.every((row) => row && row.id != null && row.user_id != null && ['income', 'expense'].includes(row.type) && typeof row.amount === 'string' && typeof row.category === 'string' && typeof row.created_at === 'string'));
    return () => controller.abort();
  }, [version]);
  return <div className="shell"><aside className="sidebar"><a href="/" className="brand"><span className="brand-icon">◇</span>finansovik<span className="brand-dot">.</span></a><p className="menu-label">МЕНЮ</p><div className="nav-active">▦ <span>Огляд</span></div><div className="side-note"><strong>Ваша фінансова панель</strong><p>Усі записи в одному місці.</p></div></aside>
    <div className="main"><header className="topbar"><span>Finansovik <span className="divider">/</span> <strong>Огляд</strong></span><small>ФІНАНСОВА ПАНЕЛЬ</small></header><main className="content"><div className="hero"><div><div className="eyebrow">● &nbsp; ФІНАНСИ ПІД КОНТРОЛЕМ</div><h1>Огляд фінансів<span>.</span></h1><p>Доходи, витрати та всі ваші транзакції в одному місці.</p></div><button type="button" className="secondary refresh" onClick={refresh}><SymbolIcon type="reload" /> Оновити дані</button></div>
      <section><div className="section-title"><div><h2>Підсумок</h2><p>Загальна картина за весь час</p></div><span className="section-caption">ЗА ВЕСЬ ЧАС</span></div><Summary state={summary} reload={refresh} /></section>
      <TransactionForm onSaved={refresh} /><TransactionTable state={transactions} onRefresh={refresh} /><footer><span>© Finansovik</span><span>Дані з вашої бази · Локальний перегляд</span></footer>
    </main></div></div>;
}
