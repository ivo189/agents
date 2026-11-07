/** Inbox Cleaner (Apps Script). Requiere habilitar el servicio avanzado "Gmail API". */
const CFG = {
  maxMinutes: 4.5, // Apps Script corta a los 6 min: si falta, volvé a ejecutar y sigue.
  keep: ['anchapebot@gmail.com', 'property.booking.com'],
  priority: [
    {label: 'Prioridad/Finanzas', from: ['bancogalicia.com.ar', 'cajadevalores.com.ar', 'interactivebrokers.com',
      'uala.mx', 'mercadopago.com', 'cocos.capital', 'nu@nu.com.mx', 'mails.santander.com.ar', 'hipotecario.com.ar']},
    {label: 'Prioridad/Impuestos', from: ['sat.gob.mx', 'arca.gob.ar', 'afip.gob.ar']},
    {label: 'Prioridad/Viajes', from: ['noreply@booking.com', 'property.booking.com']},
  ],
};
const SHEET = 'Remitentes', CONTACTS = 'Contactos';
const HEAD = ['email', 'nombre', 'sin_leer', 'pct_promo', 'tiene_baja', 'one_click', 'decision', 'motivo', 'estado', 'url_baja', 'baja'];
const VALID = ['keep', 'unsub', 'trash', 'review'];

function onOpen() {
  SpreadsheetApp.getUi().createMenu('Inbox Cleaner')
    .addItem('1. Inventario', 'inventory').addSeparator()
    .addItem('2a. Limpiar (simulación)', 'cleanDry').addItem('2b. Limpiar (APLICAR)', 'cleanApply').addSeparator()
    .addItem('3. Desuscribir one-click (APLICAR)', 'unsubscribe')
    .addItem('4. Prioridades (APLICAR)', 'prioritize').addToUi();
}
const alertUi = (m) => SpreadsheetApp.getUi().alert(m);
const sheet = (n) => SpreadsheetApp.getActive().getSheetByName(n || SHEET) || SpreadsheetApp.getActive().insertSheet(n || SHEET);
const deadline = () => Date.now() + CFG.maxMinutes * 60000;

// ---------- utilidades Gmail ----------
function withRetry(fn) {
  for (let i = 0; ; i++) {
    try { return fn(); } catch (e) {
      if (i >= 4 || !/quota|rate|429|backend|unavailable/i.test(String(e))) throw e;
      Utilities.sleep(15000 * (i + 1));
    }
  }
}
function listIds(q, max) {
  const ids = []; let pt;
  do {
    const r = withRetry(() => Gmail.Users.Messages.list('me', {q: q, maxResults: 500, pageToken: pt}));
    (r.messages || []).forEach((m) => ids.push(m.id)); pt = r.nextPageToken;
  } while (pt && (!max || ids.length < max));
  return ids;
}
function fetchMeta(ids, headers, limit) {
  const token = ScriptApp.getOAuthToken(), out = [];
  const qs = headers.map((h) => 'metadataHeaders=' + h).join('&');
  const queue = ids.slice(); let size = 25;
  while (queue.length && Date.now() < limit) {
    const chunk = queue.splice(0, size), failed = [];
    const res = UrlFetchApp.fetchAll(chunk.map((id) => ({
      url: 'https://gmail.googleapis.com/gmail/v1/users/me/messages/' + id + '?format=metadata&' + qs,
      headers: {Authorization: 'Bearer ' + token}, muteHttpExceptions: true})));
    res.forEach((r, k) => {
      const c = r.getResponseCode();
      if (c === 200) out.push(JSON.parse(r.getContentText())); else if (c === 429 || c === 403) failed.push(chunk[k]);
    });
    if (failed.length) { queue.unshift.apply(queue, failed); size = Math.max(5, size >> 1); Utilities.sleep(20000); }
    else Utilities.sleep(800);
  }
  return out;
}
const hdr = (m, n) => ((m.payload.headers || []).find((h) => h.name.toLowerCase() === n.toLowerCase()) || {}).value || '';
const parseFrom = (s) => { const m = s.match(/^\s*"?([^"<]*?)"?\s*<([^>]+)>/); return m ? [m[1].trim(), m[2].toLowerCase()] : ['', s.trim().toLowerCase()]; };
function modify(ids, add, remove) {
  for (let i = 0; i < ids.length; i += 1000)
    withRetry(() => Gmail.Users.Messages.batchModify({ids: ids.slice(i, i + 1000), addLabelIds: add, removeLabelIds: remove}, 'me'));
}
function makeFilters(emails, action) {
  for (let i = 0; i < emails.length; i += 40)
    withRetry(() => Gmail.Users.Settings.Filters.create(
      {criteria: {query: 'from:(' + emails.slice(i, i + 40).join(' OR ') + ')'}, action: action}, 'me'));
}
const protectedBy = (e) => CFG.keep.some((p) => e.includes(p)) ? 'config.keep'
  : (CFG.priority.find((r) => r.from.some((p) => e.includes(p))) || {label: ''}).label && 'prioridad';

// ---------- 1. inventario ----------
function inventory() {
  const t0 = Date.now(), tContacts = t0 + 60000, tEnd = deadline();
  const contacts = new Set();
  fetchMeta(listIds('in:sent', 500), ['To', 'Cc'], tContacts).forEach((m) =>
    ['To', 'Cc'].forEach((f) => hdr(m, f).split(',').forEach((p) => { const e = parseFrom(p)[1]; if (e.includes('@')) contacts.add(e); })));
  const ids = listIds('is:unread', 15000);
  const metas = fetchMeta(ids, ['From', 'List-Unsubscribe', 'List-Unsubscribe-Post'], tEnd);
  const agg = {};
  metas.forEach((m) => {
    const [name, email] = parseFrom(hdr(m, 'From'));
    const a = agg[email] = agg[email] || {name: name, n: 0, promo: 0, unsub: '', post: false};
    a.n++; if ((m.labelIds || []).includes('CATEGORY_PROMOTIONS')) a.promo++;
    const u = hdr(m, 'List-Unsubscribe');
    if (u) { a.unsub = u; a.post = /one-click/i.test(hdr(m, 'List-Unsubscribe-Post')); }
  });
  const rows = Object.keys(agg).sort((x, y) => agg[y].n - agg[x].n).map((e) => {
    const a = agg[e], pct = Math.round(100 * a.promo / a.n), why = protectedBy(e);
    let d, motivo;
    if (contacts.has(e)) { d = 'keep'; motivo = 'le escribiste alguna vez'; }
    else if (why) { d = 'keep'; motivo = why; }
    else if (pct >= 60) { d = a.unsub ? 'unsub' : 'trash'; motivo = a.unsub ? 'promo con baja' : 'promo sin baja'; }
    else { d = 'review'; motivo = 'no es promo: decidilo vos'; }
    const https = (a.unsub.match(/<(https:[^>]+)>/) || [])[1] || '';
    return [e, a.name, a.n, pct, a.unsub ? 'si' : 'no', a.post ? 'si' : 'no', d, motivo, '', https, ''];
  });
  const sh = sheet(); sh.clear(); sh.appendRow(HEAD);
  if (rows.length) sh.getRange(2, 1, rows.length, HEAD.length).setValues(rows);
  sh.setFrozenRows(1);
  const cs = sheet(CONTACTS); cs.clear();
  const list = Array.from(contacts).map((e) => [e]);
  if (list.length) cs.getRange(1, 1, list.length, 1).setValues(list);
  alertUi('Escaneados ' + metas.length + ' de ' + ids.length + ' no leídos, ' + rows.length + ' remitentes.\n' +
    'Revisá la columna "decision" (keep | unsub | trash | review).');
}

// ---------- 2. limpieza ----------
function cleanDry() { runClean(false); }
function cleanApply() { runClean(true); }
function runClean(apply) {
  const sh = sheet(), rows = sh.getDataRange().getValues(), limit = deadline();
  let total = 0, n = 0, cut = false; const done = [];
  for (let r = 1; r < rows.length; r++) {
    const d = String(rows[r][6]).trim().toLowerCase();
    if (VALID.indexOf(d) < 0) { alertUi('Decisión inválida "' + d + '" en la fila ' + (r + 1)); return; }
    if ((d !== 'trash' && d !== 'unsub') || rows[r][8] === 'limpio') continue;
    if (Date.now() > limit) { cut = true; break; }
    const ids = listIds('from:' + rows[r][0] + ' is:unread -is:starred');
    total += ids.length; n++;
    if (apply) { modify(ids, ['TRASH'], ['INBOX', 'UNREAD']); sh.getRange(r + 1, 9).setValue('limpio'); done.push(rows[r][0]); }
  }
  if (apply && done.length) makeFilters(done, {addLabelIds: ['TRASH'], removeLabelIds: ['INBOX']});
  alertUi((apply ? 'A la papelera: ' : 'Simulación: iría a la papelera ') + total + ' mensajes de ' + n + ' remitentes.' +
    (cut ? '\nSe acabó el tiempo: volvé a ejecutar para seguir.' : ''));
}

// ---------- 3. baja one-click ----------
function unsubscribe() {
  const sh = sheet(), rows = sh.getDataRange().getValues(), limit = deadline(); let ok = 0, manual = 0;
  for (let r = 1; r < rows.length && Date.now() < limit; r++) {
    if (String(rows[r][6]).trim().toLowerCase() !== 'unsub' || rows[r][10]) continue;
    if (rows[r][5] === 'si' && rows[r][9]) {
      try {
        const res = UrlFetchApp.fetch(rows[r][9], {method: 'post', payload: 'List-Unsubscribe=One-Click', muteHttpExceptions: true});
        sh.getRange(r + 1, 11).setValue('ok ' + res.getResponseCode()); ok++;
      } catch (e) { sh.getRange(r + 1, 11).setValue('fallo'); }
    } else { sh.getRange(r + 1, 11).setValue('manual (abrir link / ya filtrado)'); manual++; }
  }
  alertUi('Bajas one-click enviadas: ' + ok + '. Manuales: ' + manual + ' (el filtro de limpieza ya los manda a la papelera).');
}

// ---------- 4. prioridades ----------
function labelId(name) {
  const l = (Gmail.Users.Labels.list('me').labels || []).find((x) => x.name === name);
  return l ? l.id : Gmail.Users.Labels.create({name: name}, 'me').id;
}
function prioritize() {
  const cs = sheet(CONTACTS), people = cs.getLastRow() ? cs.getRange(1, 1, cs.getLastRow(), 1).getValues().map((x) => x[0])
    .filter((e) => !/no-?reply|donotreply|mailer-daemon/.test(e)) : [];
  const rules = CFG.priority.concat([{label: 'Prioridad/Personas', from: people}]); let n = 0;
  rules.forEach((rule) => {
    if (!rule.from.length) return;
    const id = labelId(rule.label);
    makeFilters(rule.from, {addLabelIds: [id, 'IMPORTANT']});
    for (let i = 0; i < rule.from.length; i += 40) {
      const ids = listIds('in:inbox from:(' + rule.from.slice(i, i + 40).join(' OR ') + ')');
      modify(ids, [id, 'IMPORTANT'], []); n += ids.length;
    }
  });
  alertUi('Etiquetados ' + n + ' mensajes existentes y creados los filtros para los futuros.');
}
