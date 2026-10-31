"""Small standalone adapters for Coordinator-style role metadata and routing.

The full production registry/MCP runtime is not imported. See docs/REUSE.md.
"""
from dataclasses import dataclass
import re
from .runtime import Tool
from .tools import default_tools


@dataclass(frozen=True)
class RoleDefinition:
    role_id: str
    upstream_role: str
    capabilities: tuple[str, ...]
    tool_names: tuple[str, ...]
    instruction: str


ROLES = {
    'log_analyst': RoleDefinition('log_analyst','log-analytics-agent',('log-search','log-correlation'),
        ('service_status','search_logs'),'Explain the synthetic log evidence and its limits.'),
    'trace_analyst': RoleDefinition('trace_analyst','observability-agent',('trace-analysis','latency-analysis'),
        ('service_status','inspect_trace'),'Inspect the synthetic trace and identify the slow operation.'),
    'security_analyst': RoleDefinition('security_analyst','security-threat-agent',('audit-analysis','access-review'),
        ('service_status','read_security_events'),'Explain the synthetic authorization evidence. Never perform remediation.'),
}
ROLE_IDS = ('coordinator', *ROLES)


def select_role(requested, prompt):
    if not isinstance(requested,str) or requested not in ROLE_IDS or not isinstance(prompt,str):
        raise ValueError('Unknown role or invalid prompt')
    if requested != 'coordinator': return ROLES[requested]
    if re.search(r'\b(security|permission|denied|access|policy|audit)\b',prompt,re.I):return ROLES['security_analyst']
    if re.search(r'\b(trace|span|latency|waterfall)\b',prompt,re.I):return ROLES['trace_analyst']
    return ROLES['log_analyst']


def _trace():
    return {'source':'synthetic','scenario':'checkout-timeout','spans':[
        {'operation':'checkout','duration_ms':620,'status':'timeout'},
        {'operation':'reserve_inventory','duration_ms':590,'status':'error'}]}


def _security():
    return {'source':'synthetic','scenario':'workshop-policy','events':[
        {'action':'investigate','decision':'allowed'},
        {'action':'restart_service','decision':'approval_required'}]}


def tools_for_role(role_id, fail_tool=False):
    spec=select_role(role_id,'')
    tools=default_tools(fail_tool=fail_tool)+[
        Tool('inspect_trace','Inspect a bounded synthetic checkout trace',
             {'type':'object','properties':{},'additionalProperties':False},_trace),
        Tool('read_security_events','Read bounded synthetic access-decision events',
             {'type':'object','properties':{},'additionalProperties':False},_security)]
    return [tool for tool in tools if tool.name in spec.tool_names or (fail_tool and tool.name=='controlled_failure')]
