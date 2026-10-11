# JobPilot validation — 11 October 2026

The complete suite passed: **40 tests**, including 12 JobPilot tests. Browser tests use real Chromium against intercepted local fixtures, not employer application endpoints.

Verified behavior: tracked-job deduplication, daily attempt limits, persistent submission state, exclusive run locks, password rejection, required-answer handling, tailored resume upload, explicit confirmation, uncertain submission handling, Naukri stored-resume refusal, company/date resume generation, and India-time scheduling.

Installed the documented browser extra with both constraint files and verified the `jobpilot --help` entry point.

The constrained-install rerun also passed all 40 tests. It emitted an existing Starlette deprecation warning and a Playwright teardown diagnostic about a closed browser target; the runner exited successfully. Live browser readiness remains unverified regardless of the unit-test outcome.

## Live check

A public, unauthenticated, preparation-only check returned zero jobs. LinkedIn Chromium navigation failed with `ERR_CERT_AUTHORITY_INVALID`; Naukri failed with `ERR_TUNNEL_CONNECTION_FAILED`. A separate Python request using system TLS verification reached LinkedIn but returned HTTP 429; Naukri's proxy tunnel returned HTTP 403. The proxy CA is available to the system, but Chromium trust remains unresolved. Certificate verification was not disabled.

See [live_access.json](live_access.json). No real applications were submitted. No daily service was activated. Account-specific discovery, actual portal form layouts, and real application confirmation remain unverified. These results establish a tested local prototype, not production readiness for both portals.

Users must sign in locally, configure truthful application answers, and verify current portal forms before relying on unattended execution. Unsupported forms are recorded as needing action.
