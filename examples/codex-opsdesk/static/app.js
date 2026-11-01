'use strict';
const $ = id => document.getElementById(id);
let tickets = [], selected = null, running = false, signedIn = false;
async function api(path, data) {
  const response = await fetch(path, data === undefined ? {credentials: 'same-origin'} : {
    method: 'POST', credentials: 'same-origin', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(data)
  });
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || 'The local request failed.');
  return result;
}
function node(tag, value, className) {
  const element = document.createElement(tag);
  element.textContent = value;
  if (className) element.className = className;
  return element;
}
function renderList() {
  const query = $('search').value.trim().toLowerCase();
  const priority = $('priority').value;
  const visible = tickets.filter(t => (!priority || t.priority === priority) &&
    [t.id, t.title, t.description, t.service].join(' ').toLowerCase().includes(query));
  $('ticket-list').replaceChildren();
  $('count').textContent = `${visible.length} / ${tickets.length}`;
  $('list-status').textContent = visible.length ? '' : 'No matching tickets. Try another search or priority.';
  $('list-status').hidden = visible.length > 0;
  for (const ticket of visible) {
    const row = node('button', '', 'ticket-row');
    row.type = 'button';
    row.setAttribute('aria-pressed', String(selected?.id === ticket.id));
    const top = node('span', '', 'row-top');
    top.append(node('span', ticket.id), node('span', ticket.priority, `badge ${ticket.priority}`));
    row.append(top, node('span', ticket.title, 'row-title'), node('span', ticket.service, 'row-service'));
    row.addEventListener('click', () => selectTicket(ticket));
    $('ticket-list').append(row);
  }
}
function selectTicket(ticket) {
  selected = ticket;
  $('ticket-id').textContent = ticket.id;
  $('detail-title').textContent = ticket.title;
  $('detail-meta').textContent = `${ticket.service} / ${ticket.priority} priority`;
  $('detail-description').textContent = ticket.description;
  $('analyze').disabled = running || !signedIn;
  $('policy').disabled = running || !signedIn;
  $('ai-result').textContent = 'No investigation has run for this selected ticket.';
  $('agent-events').replaceChildren();
  $('private-identifiers').hidden = true;
  $('private-identifiers').open = false;
  $('trace-identifiers').textContent = '';
  renderList();
}
async function load() {
  $('retry').hidden = true;
  $('list-status').hidden = false;
  $('list-status').textContent = 'Loading synthetic tickets…';
  try {
    tickets = (await api('/api/tickets')).tickets;
    if (tickets.length) selectTicket(tickets[0]);
    else renderList();
  } catch (error) {
    $('list-status').textContent = error.message;
    $('retry').hidden = false;
  }
}
$('search').addEventListener('input', renderList);
$('priority').addEventListener('change', renderList);
$('retry').addEventListener('click', load);
$('new-ticket').addEventListener('click', () => { $('form-error').textContent = ''; $('ticket-dialog').showModal(); });
$('close-dialog').addEventListener('click', () => $('ticket-dialog').close());
$('ticket-form').addEventListener('submit', async event => {
  event.preventDefault();
  const data = Object.fromEntries(new FormData(event.currentTarget));
  if (!data.title.trim() || !data.description.trim()) {
    $('form-error').textContent = 'Title and description must contain text.';
    return;
  }
  $('submit-ticket').disabled = true;
  $('submit-ticket').textContent = 'Creating…';
  $('form-error').textContent = '';
  try {
    const ticket = await api('/api/tickets', data);
    tickets.push(ticket);
    $('search').value = '';
    $('priority').value = '';
    selectTicket(ticket);
    $('ticket-dialog').close();
    $('ticket-form').reset();
  } catch (error) { $('form-error').textContent = error.message; }
  finally { $('submit-ticket').disabled = false; $('submit-ticket').textContent = 'Create ticket'; }
});
async function refreshStatus() {
  const status = await api('/api/status');
  signedIn = status.signed_in;
  $('login-form').hidden = signedIn;
  $('logout').hidden = !signedIn;
  $('auth-status').textContent = signedIn ? 'Signed in · presenter session' : 'Sign in required before model calls or ticket creation.';
  $('connection').textContent = status.model_configured ? status.model : 'Model not configured';
  $('connection').title = 'Quota mode: ' + status.quota_mode;
  $('analyze').disabled = running || !selected || !signedIn;
  $('policy').disabled = running || !selected || !signedIn;
}
$('login-form').addEventListener('submit', async event => {
  event.preventDefault();
  const value = $('password').value;
  $('password').value = '';
  try { await api('/api/login', {password: value}); await refreshStatus(); }
  catch (error) { $('auth-status').textContent = error.message; }
});
$('logout').addEventListener('click', async () => {
  try { await api('/api/logout', {}); await refreshStatus(); }
  catch (error) { $('auth-status').textContent = error.message; }
});
async function investigate(action) {
  if (!selected || running || !signedIn) return;
  const submittedTicket = {id: selected.id, service: selected.service};
  const submittedReview = $('review').checked;
  running = true;
  $('analyze').disabled = $('policy').disabled = true;
  $('ai-result').textContent = 'Running the bounded server harness…';
  $('agent-events').replaceChildren();
  $('private-identifiers').hidden = true;
  $('private-identifiers').open = false;
  try {
    const run = await api('/api/investigate', {service: submittedTicket.service, action, review: submittedReview});
    // An asynchronous answer belongs only to the exact ticket/service submitted.
    if (!selected || selected.id !== submittedTicket.id || selected.service !== submittedTicket.service) return;
    const lines = ['Ticket: ' + submittedTicket.id + ' · service: ' + submittedTicket.service, run.outcome, 'Actual model calls: ' + run.model_calls];
    if (run.answer) lines.push('Investigator: ' + run.answer);
    if (run.review) lines.push('Reviewer: ' + run.review);
    lines.push('Reviewer status: ' + run.review_status);
    lines.push('Reported usage: ' + (run.usage ? JSON.stringify(run.usage) : 'unknown'));
    lines.push('Uncached catalog estimate: ' + (run.cost ? '$' + run.cost.usd.toFixed(6) + ' · estimate, not a bill · source as of ' + run.cost.as_of : 'unknown'));
    lines.push('Langfuse export: ' + run.telemetry.status + ' · independent readback: ' + run.telemetry.readback);
    if (run.error) lines.push(run.error);
    $('ai-result').textContent = lines.join('\n\n');
    for (const agent of run.agent_summaries) {
      $('agent-events').append(node('p', 'Agent ' + agent.role + ' · calls: ' + agent.model_calls + ' · reported usage: ' + (agent.usage ? JSON.stringify(agent.usage) : 'unknown') + ' · uncached estimate: ' + (agent.cost ? '$' + agent.cost.usd.toFixed(6) : 'unknown')));
    }
    for (const agent of run.agents) {
      $('agent-events').append(node('p', agent.role + ' · returned model: ' + agent.model + ' · usage: ' + (agent.usage ? JSON.stringify(agent.usage) : 'unknown') + ' · uncached estimate: ' + (agent.cost ? '$' + agent.cost.usd.toFixed(6) : 'unknown')));
    }
    for (const event of run.events) $('agent-events').append(node('p', 'Actual event: ' + JSON.stringify(event)));
    if (run.trace_id) {
      $('trace-identifiers').textContent = 'Trace: ' + run.trace_id + '\nRandom session: ' + (run.telemetry.session_label || 'not reported');
      $('private-identifiers').hidden = false;
    }
  } catch (error) {
    if (selected && selected.id === submittedTicket.id && selected.service === submittedTicket.service) {
      $('ai-result').textContent = error.message + ' No automatic retry.';
    }
  }
  finally { running = false; await refreshStatus(); }
}
$('analyze').addEventListener('click', () => investigate('investigate'));
$('policy').addEventListener('click', () => investigate('change'));
load().then(refreshStatus).catch(() => { $('auth-status').textContent = 'Setup check failed; no automatic retry.'; });
