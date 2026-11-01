"""Small, explicit server boundaries; no identity chosen by the browser."""
import base64
import hashlib
import hmac
import json
import secrets
import threading
import time
from http.cookies import SimpleCookie, CookieError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

MAX_BODY = 4096
SERVICES = ('payments', 'checkout', 'catalog')
ACTIONS = ('investigate', 'change', 'remediate', 'restart')


class Invalid(ValueError):
    pass


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *_args, **_kwargs):
        return None


def json_post(url, data, headers, timeout=10, limit=524288):
    """Exactly one HTTPS request. Redirects are errors, never credential forwards."""
    if urlsplit(url).scheme != 'https':
        raise Invalid('HTTPS destination required.')
    request = Request(url, data=json.dumps(data).encode(), headers={
        'Content-Type': 'application/json', **headers}, method='POST')
    with build_opener(NoRedirect).open(request, timeout=timeout) as response:
        raw = response.read(limit + 1)
        if len(raw) > limit:
            raise Invalid('Provider response exceeded the limit.')
        return json.loads(raw)


def exact(data, fields):
    if type(data) is not dict or set(data) != set(fields):
        raise Invalid('Unexpected or missing fields.')


def choice(value, choices):
    if type(value) is not str or value not in choices:
        raise Invalid('Unsupported value.')
    return value


def text(value, limit):
    if type(value) is not str or not 1 <= len(value.strip()) <= limit:
        raise Invalid('Text is empty or exceeds its limit.')
    return value.strip()


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise Invalid('Duplicate JSON fields.')
        result[key] = value
    return result


def valid_origin(value, deployed=False):
    try:
        parsed = urlsplit(value)
        port = parsed.port
        if parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path:
            return False
        if deployed:
            return parsed.scheme == 'https' and bool(parsed.hostname) and port in (None, 443)
        return parsed.scheme == 'http' and parsed.hostname == '127.0.0.1' and port is not None
    except ValueError:
        return False


class Sessions:
    cookie_name = 'opsdesk_session'

    def __init__(self, login_secret, signing_secret, secure=True, clock=time.time):
        self.login_secret, self.signing_secret = login_secret, signing_secret
        self.secure, self.clock = secure, clock

    @property
    def configured(self):
        return len(self.login_secret) >= 32 and len(self.signing_secret) >= 32

    def issue(self, password):
        if not self.configured or type(password) is not str or len(password) > 256:
            return None
        if not hmac.compare_digest(password.encode(), self.login_secret.encode()):
            return None
        payload = base64.urlsafe_b64encode(json.dumps({
            'expires': int(self.clock()) + 3600, 'nonce': secrets.token_hex(16),
            'role': 'presenter'}, separators=(',', ':')).encode()).decode().rstrip('=')
        signature = hmac.new(self.signing_secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
        return self.cookie(payload + '.' + signature)

    def cookie(self, value, max_age=3600):
        return (f'{self.cookie_name}={value}; Path=/; HttpOnly; SameSite=Strict; Max-Age={max_age}'
                + ('; Secure' if self.secure else ''))

    def authenticate(self, raw_cookie):
        if not self.configured or type(raw_cookie) is not str or len(raw_cookie) > 2048:
            return False
        try:
            cookie = SimpleCookie(); cookie.load(raw_cookie or '')
            value = cookie[self.cookie_name].value
            payload, signature = value.split('.')
            expected = hmac.new(self.signing_secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
            if not hmac.compare_digest(signature, expected):
                return False
            decoded = json.loads(base64.urlsafe_b64decode(payload + '=' * (-len(payload) % 4)))
            return decoded['role'] == 'presenter' and type(decoded['expires']) is int and self.clock() < decoded['expires'] <= self.clock() + 3600
        except (ValueError, KeyError, TypeError, CookieError):
            return False


class LocalQuota:
    """Explicit single-process local rehearsal only; never a serverless fallback."""
    mode = 'local_single_process'

    def __init__(self, clock=time.time):
        self.clock, self.lock, self.counts = clock, threading.Lock(), {}

    def reserve(self):
        now = int(self.clock()); keys = [('minute', now // 60), ('day', now // 86400)]
        with self.lock:
            if self.counts.get(keys[0], 0) >= 2 or self.counts.get(keys[1], 0) >= 10:
                return False
            for key in keys:
                self.counts[key] = self.counts.get(key, 0) + 1
            self.counts = {key: value for key, value in self.counts.items() if key in keys}
        return True


class RedisQuota:
    """Atomic shared per-presenter minute/day reservation in one Redis Lua call."""
    mode = 'redis_atomic'
    script = '''local m=tonumber(redis.call('GET',KEYS[1]) or '0')
local d=tonumber(redis.call('GET',KEYS[2]) or '0')
if m>=2 or d>=10 then return 0 end
redis.call('INCR',KEYS[1]);redis.call('EXPIRE',KEYS[1],120)
redis.call('INCR',KEYS[2]);redis.call('EXPIRE',KEYS[2],172800)
return 1'''

    def __init__(self, url, token, prefix, clock=time.time, transport=json_post):
        parsed = urlsplit(url)
        if (parsed.scheme != 'https' or not parsed.hostname or not parsed.hostname.endswith('.upstash.io')
                or parsed.username or parsed.password or parsed.path not in ('', '/') or parsed.query or parsed.fragment):
            raise Invalid('Expected the owned Upstash HTTPS origin.')
        if not token or not prefix or len(prefix) > 80:
            raise Invalid('Quota configuration missing.')
        self.url, self.token, self.prefix = url.rstrip('/'), token, prefix
        self.clock, self.transport = clock, transport

    def reserve(self):
        now = int(self.clock())
        # Fixed server identity, not a user-provided session or IP.
        keys = [f'opsdesk:{self.prefix}:presenter:m:{now // 60}', f'opsdesk:{self.prefix}:presenter:d:{now // 86400}']
        reply = self.transport(self.url, ['EVAL', self.script, '2', *keys],
                               {'Authorization': 'Bearer ' + self.token}, timeout=5)
        if type(reply) is not dict or type(reply.get('result')) is not int:
            raise Invalid('Quota store unavailable.')
        return reply['result'] == 1
