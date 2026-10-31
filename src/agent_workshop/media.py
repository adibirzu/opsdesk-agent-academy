"""Optional read-only media discovery; never connects a Google/Discord account."""
import hashlib
import json
import os
from pathlib import Path
import re
import urllib.error
import urllib.request

ENDPOINT = 'https://openflowmcp.com/mcp'
PROTOCOL = '2025-06-18'
MAX_BYTES = 512 * 1024
READ_TOOLS = ('flow_status', 'flow_health', 'check_credits', 'list_models', 'check_job')
NAME = re.compile(r'[A-Za-z][A-Za-z0-9_.-]{0,95}')


class MediaError(ValueError):
    """Safe error without remote bodies or credential values."""


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise MediaError('Provider redirect refused; no credential forwarding')


def private_directory(path, root=None):
    root = (root or Path(__file__).resolve().parents[2]).resolve()
    path = Path(path).expanduser()
    resolved = path.resolve()
    if path.exists() or path.is_symlink():
        raise MediaError('Select a new private output directory')
    if resolved.is_relative_to(root) and not resolved.is_relative_to(root / 'local/private'):
        raise MediaError('Inside the checkout, use local/private for media artifacts')
    path.mkdir(parents=True, mode=0o700)
    path.chmod(0o700)
    return path.resolve()


def write_private(path, text):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as handle:
        handle.write(text)


def parse_response(data, content_type, expected_id):
    if len(data) > MAX_BYTES:
        raise MediaError('Provider response exceeds the size limit')
    try:
        if content_type == 'application/json':
            messages = [json.loads(data)]
        elif content_type == 'text/event-stream':
            messages = []
            for event in data.decode('utf-8').replace('\r\n', '\n').split('\n\n'):
                payload = '\n'.join(line[5:].lstrip(' ') for line in event.splitlines() if line.startswith('data:'))
                if payload:
                    messages.append(json.loads(payload))
        else:
            raise MediaError('Unsupported provider response type')
    except (UnicodeError, ValueError) as exc:
        raise MediaError('Invalid provider response') from None
    matches = []
    for message in messages:
        if not isinstance(message, dict) or message.get('jsonrpc') != '2.0' or 'method' in message:
            raise MediaError('Server-driven requests and notifications are unsupported')
        if type(message.get('id')) is not int or message['id'] != expected_id:
            raise MediaError('Provider response ID mismatch')
        if 'error' in message or not isinstance(message.get('result'), dict):
            raise MediaError('Provider rejected the MCP request')
        matches.append(message['result'])
    if len(matches) != 1:
        raise MediaError('Expected exactly one matching MCP response')
    return matches[0]


class OpenFlowCatalog:
    """Bounded MCP handshake and catalog only; no tools/call or registration."""
    def __init__(self, token=None, opener=None):
        if token is not None and (not isinstance(token, str) or not re.fullmatch(r'[!-~]{1,4096}', token)):
            raise MediaError('Invalid provider token')
        self.token = token
        self.opener = opener or urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
        self.session = None
        self.protocol = None

    def request(self, method, params=None, identifier=None):
        if method not in {'initialize', 'notifications/initialized', 'tools/list'}:
            raise MediaError('This client permits handshake and catalog discovery only')
        return self._send(method, params, identifier)

    def _send(self, method, params=None, identifier=None):
        message = {'jsonrpc': '2.0', 'method': method}
        if identifier is not None:
            message['id'] = identifier
        if params is not None:
            message['params'] = params
        headers = {'Content-Type': 'application/json', 'Accept': 'application/json, text/event-stream'}
        if self.token:
            headers['Authorization'] = 'Bearer ' + self.token
        if self.session:
            headers['Mcp-Session-Id'] = self.session
        if self.protocol:
            headers['MCP-Protocol-Version'] = self.protocol
        request = urllib.request.Request(ENDPOINT, data=json.dumps(message).encode(), headers=headers, method='POST')
        try:
            with self.opener.open(request, timeout=20) as response:
                if response.status not in (200, 202) or response.geturl() != ENDPOINT:
                    raise MediaError('Unexpected provider response or destination')
                session = response.headers.get('Mcp-Session-Id')
                if session:
                    if not re.fullmatch(r'[!-~]{1,256}', session) or (self.session and session != self.session):
                        raise MediaError('Invalid or changed MCP session')
                    self.session = session
                data = response.read(MAX_BYTES + 1)
                if identifier is None:
                    if response.status != 202 or data:
                        raise MediaError('Unexpected initialization notification response')
                    return None
                return parse_response(data, response.headers.get_content_type(), identifier)
        except urllib.error.HTTPError as exc:
            if exc.code in (401, 403):
                raise MediaError('Provider authentication required; no account was registered or connected') from None
            raise MediaError('Provider HTTP request failed; no automatic retry') from None
        except (urllib.error.URLError, TimeoutError, OSError):
            raise MediaError('Provider transport unavailable; no automatic retry') from None

    def catalog(self):
        result = self.request('initialize', {'protocolVersion': PROTOCOL, 'capabilities': {}, 'clientInfo': {'name': 'agent-workshop-media-catalog', 'version': '0.1.0'}}, 1)
        if result.get('protocolVersion') != PROTOCOL:
            raise MediaError('Unsupported negotiated MCP version')
        self.protocol = PROTOCOL
        self.request('notifications/initialized')
        result = self.request('tools/list', {}, 2)
        if result.get('nextCursor'):
            raise MediaError('Catalog is paginated; incomplete discovery is not accepted')
        tools = result.get('tools')
        if not isinstance(tools, list) or len(tools) > 200:
            raise MediaError('Invalid or oversized tool catalog')
        normalized = []
        for tool in tools:
            if not isinstance(tool, dict) or not NAME.fullmatch(str(tool.get('name', ''))):
                raise MediaError('Invalid tool name')
            schema = tool.get('inputSchema', {})
            properties = schema.get('properties', {}) if isinstance(schema, dict) else None
            if not isinstance(properties, dict) or len(properties) > 100 or any(not NAME.fullmatch(str(k)) for k in properties):
                raise MediaError('Invalid tool schema')
            normalized.append({'name': tool['name'], 'argument_names': sorted(properties), 'read_allowlisted': tool['name'] in READ_TOOLS})
        if len({t['name'] for t in normalized}) != len(normalized):
            raise MediaError('Duplicate tool names')
        return {'endpoint': ENDPOINT, 'protocol': PROTOCOL, 'tools': normalized, 'tool_calls_made': 0, 'account_connected_by_client': False}


class OpenFlowReadOnly(OpenFlowCatalog):
    """Authenticated, fixed read tools; returned content is untrusted data."""
    def call(self, name, arguments=None):
        if not self.token or not self.protocol:
            raise MediaError('Initialize with an approved provider key before readback')
        if name not in READ_TOOLS:
            raise MediaError('Only the five approved read tools are permitted')
        arguments = {} if arguments is None else arguments
        if not isinstance(arguments, dict):
            raise MediaError('Read tool arguments must be an object')
        if name == 'check_job':
            if set(arguments) != {'job_id'} or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', str(arguments['job_id'])):
                raise MediaError('A bounded job identifier is required')
        elif arguments:
            raise MediaError('Account and model read tools accept no arguments here')
        self._read_id = getattr(self, '_read_id', 2) + 1
        result = self._send('tools/call', {'name': name, 'arguments': arguments}, self._read_id)
        if result.get('isError'):
            raise MediaError('Provider read tool failed; remote instructions were not executed')
        return result


def prepare(provider, output, include_generation=False):
    if provider not in {'openflow', 'midjourney'}:
        raise MediaError('Choose openflow or midjourney')
    if include_generation and provider != 'openflow':
        raise MediaError('Midjourney is human submission only')
    directory = private_directory(output)
    prompt = ('An editorial illustration of a small AI agent inside a transparent console, '
              'three visible paths for traces, logs and security decisions, warm ivory background, '
              'teal and terracotta accents, wide composition, no logos, no text, synthetic data only.')
    write_private(directory / 'prompt.txt', prompt + '\n')
    if provider == 'openflow':
        config = ('# Merge manually only after reviewing hosted account access and gallery settings.\n'
                  '[mcp_servers.openflow_workshop]\n'
                  f'url = "{ENDPOINT}"\n'
                  'bearer_token_env_var = "OPENFLOW_MCP_TOKEN"\n'
                  'enabled = false\n'
                  'default_tools_approval_mode = "prompt"\n'
                  'enabled_tools = ' + json.dumps(list(READ_TOOLS) + (['generate_image', 'generate_video'] if include_generation else [])) + '\n')
        write_private(directory / 'codex-fragment.toml', config)
    mode = ('disabled_generation_mcp' if include_generation else 'disabled_read_only_mcp') if provider == 'openflow' else 'human_submission_only'
    report = {'provider': provider, 'mode': mode, 'network_calls': 0, 'credentials_written': False, 'prompt_sha256': hashlib.sha256(prompt.encode()).hexdigest()}
    write_private(directory / 'receipt.json', json.dumps(report, indent=2))
    return report
