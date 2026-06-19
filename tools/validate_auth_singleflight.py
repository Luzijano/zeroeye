#!/usr/bin/env python3
"""Validate auth refresh single-flight implementation invariants."""
from pathlib import Path

source = Path('frontend/src/services/auth.ts').read_text(encoding='utf-8')
required = [
    'let refreshInFlight: Promise<AuthTokens | null> | null = null',
    'if (refreshInFlight) return refreshInFlight',
    'readRefreshMarker()',
    'waitForCrossTabRefresh(existingMarker.refreshId)',
    "broadcastRefresh({ type: 'refresh-complete', refreshId })",
    "broadcastRefresh({ type: 'refresh-failed', refreshId })",
    'finally {',
    'clearRefreshMarker(refreshId)',
    'refreshInFlight = null',
    'REFRESH_IN_FLIGHT_TTL_MS',
]
missing = [item for item in required if item not in source]
if missing:
    raise SystemExit('missing single-flight invariant(s): ' + ', '.join(missing))

# Broadcast messages must not contain raw token fields. Only refresh status/id metadata is allowed.
for forbidden in ['accessToken:', 'refreshToken:', 'tokens: response.data.tokens']:
    if forbidden in source[source.find('function broadcastRefresh'):source.find('function waitForCrossTabRefresh')]:
        raise SystemExit(f'broadcast leaks token-like field: {forbidden}')

print('auth single-flight validation passed')
