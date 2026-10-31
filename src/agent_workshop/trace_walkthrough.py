"""Inspect bounded local events without executing tools, loading secrets or exporting."""
import hashlib
import json
import math
import os
import re
import stat


STAGES = {
    'agent.route': ('routing', 'Choose the agent role and its tool allowlist.'),
    'run.start': ('start', 'Start a bounded agent run.'),
    'step.start': ('step', 'Start the next model/tool iteration.'),
    'llm.usage': ('model', 'Record reported token usage and any configured-rate estimate.'),
    'tool.start': ('tool', 'Invoke a tool after validating its name and arguments.'),
    'tool.end': ('observation', 'Return the tool observation to the harness.'),
    'tool.error': ('failure', 'Record a failed tool call.'),
    'step.error': ('failure', 'Record a failed model step.'),
    'run.error': ('failure', 'Stop an invalid action or runtime failure.'),
    'security.decision': ('security', 'Record the authorization gate decision.'),
    'coordinator.end': ('completion', 'Finish the graph; approval_required stops before inference.'),
    'run.end': ('completion', 'Record the run outcome; backend delivery needs separate proof.'),
}


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate event key')
        result[key] = value
    return result


def _tokens(value):
    if value is not None and (type(value) is not int or not 0 <= value <= 1_000_000_000):
        raise ValueError('Invalid usage metadata')
    return value


def summarize_events(path, trace_id, session_id):
    """Return a content-free projection; a local file cannot prove provider ingestion."""
    if not isinstance(trace_id, str) or not re.fullmatch('[0-9a-f]{32}', trace_id):
        raise ValueError('Select an exact trace')
    if not isinstance(session_id, str) or not re.fullmatch('[A-Za-z0-9_.:-]{1,128}', session_id):
        raise ValueError('Select an exact session')
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except OSError as exc:
        raise ValueError("Select an accessible regular event file") from exc
    with os.fdopen(fd, 'rb') as source:
        metadata = os.fstat(source.fileno())
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_size > 1_000_000:
            raise ValueError('Select a bounded regular event file')
        body = source.read(1_000_001)
    if len(body) > 1_000_000:
        raise ValueError('Event file exceeds size limit')
    lines = body.splitlines()
    if len(lines) > 5000:
        raise ValueError('Event count exceeds limit')
    selected = []
    try:
        for line in lines:
            if not line.strip():
                continue
            row = json.loads(line, object_pairs_hook=_object,
                             parse_constant=lambda _: (_ for _ in ()).throw(ValueError('Nonfinite event number')))
            if not isinstance(row, dict):
                raise ValueError('Expected event objects')
            if row.get('trace_id') == trace_id and row.get('session.id') == session_id:
                selected.append(row)
                if len(selected) > 500:
                    raise ValueError('Selected event count exceeds limit')
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError('Invalid event file') from exc
    if not selected:
        raise ValueError('No events for exact trace and session')
    timeline = []
    incoming = outgoing = usage_count = unknown = starts = ends = graph_ends = 0
    terminal_outcomes = set()
    usage_complete = cost_complete = True
    cost_total = 0.0
    outcome = 'incomplete'
    for row in selected:
        name = row.get('event')
        if not isinstance(name, str) or name not in STAGES:
            unknown += 1
            continue
        stage, explanation = STAGES[name]
        item = {'sequence': len(timeline) + 1, 'event': name, 'stage': stage, 'explanation': explanation}
        if name == 'run.start':
            starts += 1
        if name in ('run.end', 'coordinator.end'):
            ends += name == 'run.end'
            graph_ends += name == 'coordinator.end'
            outcome = row.get('status') if row.get('status') in ('success', 'failure', 'approval_required') else 'incomplete'
            terminal_outcomes.add(outcome)
            item['status'] = outcome
        if name == 'security.decision':
            item['status'] = 'approval_required' if row.get('decision') == 'approval_required' else 'unclassified'
        if name == 'llm.usage':
            usage_count += 1
            first, second = _tokens(row.get('input_tokens')), _tokens(row.get('output_tokens'))
            usage_complete = usage_complete and first is not None and second is not None
            incoming += first or 0
            outgoing += second or 0
            item.update(input_tokens=first, output_tokens=second)
            estimate = row.get('estimated_cost_usd')
            if estimate is not None and (type(estimate) not in (int, float) or not math.isfinite(estimate) or not 0 <= estimate <= 1_000_000_000):
                raise ValueError('Invalid cost metadata')
            if estimate is None or row.get('cost_basis') != 'configured_uncached_text_rates':
                cost_complete = False
            else:
                cost_total += estimate
        timeline.append(item)
    if starts > 1 or ends > 1 or graph_ends > 1 or len(terminal_outcomes) > 1:
        raise ValueError('Selection contains ambiguous run boundaries')
    return {'evidence_class': 'local_record_only', 'provider_verified': False,
            'selection': 'exact_trace_and_session', 'source_sha256': hashlib.sha256(body).hexdigest(),
            'outcome': outcome, 'timeline': timeline, 'unknown_event_count': unknown,
            'usage': {'input_tokens': incoming if usage_count and usage_complete else None,
                      'output_tokens': outgoing if usage_count and usage_complete else None,
                      'known_token_lower_bound': incoming + outgoing},
            'estimated_cost_usd': round(cost_total, 12) if usage_count and cost_complete and usage_complete else None,
            'cost_basis': 'configured_rates_only; not a provider invoice',
            'required_next': 'Query each backend for the exact trace and session; this file proves no ingestion.'}
