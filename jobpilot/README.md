# JobPilot India — LinkedIn and Naukri

**Status: local prototype; account-specific discovery and real applications are not yet validated.** No actual application has been submitted. A daily schedule has not been activated. The code has been tested with local browser fixtures; those are not real portal applications.

JobPilot extends JDMatch with a daily search/preparation loop, minimum-match filtering, one-page company/date resumes, conditional browser submission, and a persistent duplicate ledger. It runs on your computer using a browser profile where **you sign in directly**. Never send passwords, OTPs, recovery codes or session cookies in chat or commit them to GitHub.

## What it can do

- Search LinkedIn and Naukri for the configured Go/Python/cloud-native query.
- Read recognizable job descriptions and check location metadata.
- Match your existing resume using JDMatch's **internal evidence-based keyword score**, not a vendor ATS or an eligibility guarantee.
- Prepare a new one-page PDF/Word resume and evidence report for eligible matches. Your bundled profile retains its photo. The company abbreviation, India-local date and run ID appear in the filename; the company/date also appears in a footer.
- Use LinkedIn **Easy Apply** only when it identifies a supported dialog, has explicit answers for every required field, verifies a tailored resume upload, and sees a final confirmation.
- Attempt only a supported Naukri form with a clearly labeled resume upload. Naukri one-click applications using a stored account resume are left for review unless the actual tailored file can be verified. External career-site redirects are not automated.
- Remember submitted and uncertain applications; stop repeat submission after an uncertain final click.
- Repeat daily at an India-local time while the local process/machine remains running.

**It cannot promise to apply to every matching vacancy on either portal.** Login, challenges, changed selectors, custom questions, external forms and stored account resumes can prevent automation. It records these cases rather than inventing answers or reporting success. Job discovery selectors are provisional until tested against your account's actual portal pages. Site access controls are not bypassed.

## Install on your computer

Clone this branch or download its ZIP. Python 3.12/Linux is the tested runtime. Windows/macOS commands are documented but not executed here.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -c requirements.lock -c jobpilot/browser-constraints.txt -e '.[dev,browser]'
.venv/bin/python -m playwright install chromium
```

On Windows use `py -3.12 -m venv .venv` and `.venv\Scripts\python.exe` in place of `.venv/bin/python`.

The cloud validation used the already-installed `/usr/bin/chromium` with Playwright. You can set `browser_executable` to an installed browser path in your private configuration instead of downloading another browser. Do not point it at an untrusted executable.

## One-time private configuration

Copy `jobpilot/settings.example.json` to `jobpilot/settings.local.json` (this exact local filename is gitignored). It contains your verified contact details and these defaults:

- Portals: LinkedIn and Naukri.
- Minimum match: **70%**, maximum **100%**; stronger matches are included. Set maximum to 80 only if you want a strict 70–80% band.
- Location: India; recognized India locations allowed. Unknown/global-remote eligibility needs review.
- Daily limit: **10 submission attempts**, adjustable up to 100.
- Search bound: **30 cards per portal**, adjustable up to 100. This is not an exhaustive search of the entire portal.
- Work arrangement/salary: no preference is inferred. Set your portal search/account preferences and provide truthful required form answers. The current code does not implement an automatic salary filter.
- Required application answers: only contact details are preconfigured. Add exact visible question labels and truthful values to `answers`, including joining availability, compensation or work authorization when asked. Missing required answers stop submission. Checkbox/radio answers require explicit boolean values. Some forms need additional adapter work.

The example is not a ready-to-submit universal application profile. Do not invent salary, citizenship, certifications, years per skill or screening answers. The agent does not read another person's experience from the web into your resume.

## Sign in directly

```bash
.venv/bin/python -m ats_agent.jobpilot --config jobpilot/settings.local.json --login linkedin
.venv/bin/python -m ats_agent.jobpilot --config jobpilot/settings.local.json --login naukri
```

A browser opens. Type your credentials there, complete verification yourself, then return to the terminal and press Enter. The account session is stored in `.jobpilot/sessions/`, not in source or a published file. The private folder is gitignored and created with restrictive permissions on systems supporting them. Expired sessions require signing in again. Do not run overlapping browser processes using the same session profile.

## First run: preparation only

```bash
.venv/bin/python -m ats_agent.jobpilot --config jobpilot/settings.local.json
```

Inspect `.jobpilot/runs/<date>_<run-id>/daily_report.json` and the generated job-specific resumes. No submission occurs without `--submit`. Verify real portal compatibility before relying on unattended operation.

## Submission mode

```bash
.venv/bin/python -m ats_agent.jobpilot --config jobpilot/settings.local.json --submit
```

This authorizes the local process to submit supported matching applications using the saved truthful answers. Unknown required questions, unverifiable uploads, external redirects and challenges are logged for action. A final click followed by a timeout becomes `submission_unknown`; inspect your application history before any retry. The agent never automatically resubmits that job.

## Daily operation

```bash
.venv/bin/python -m ats_agent.jobpilot --config jobpilot/settings.local.json --submit --daily-at 09:00
```

This runs once per day at **09:00 Asia/Kolkata** while this terminal process and computer remain running and online. Before live portal validation, omit `--submit` for scheduled preparation only. Closing the process, sleeping/shutting down your computer, or losing network access prevents execution. ChatGPT does not itself wake up daily to run this application.

Alternatively use Windows Task Scheduler or Linux cron to run the one-shot command daily from the repository directory. Do not store passwords in the scheduled command. No OS scheduler was installed during this task; persistent hosting is not provided by this cloud-onboarding chat.

## Status meanings

| Status | Meaning |
|---|---|
| prepared | Matching resume generated; not submitted |
| below_match_range | Internal score outside configured range |
| needs_action | Login, unknown question, location, upload or unsupported form needs attention |
| submitted | Portal displayed an explicit submission confirmation |
| submission_unknown | Final action was attempted, but confirmation was not observed; no automatic retry |
| skipped_duplicate_or_pending | Ledger already records submitted/unknown/in-flight application |
| skipped | Duplicate or daily limit prevented submission |

A database record alone is not proof of an employer receiving an application. Live confirmations must be checked in the portal. The ledger deliberately favors avoiding duplicate applications if a process crashes after a final click.

## Verification and limits

Read [validation/RESULTS.md](validation/RESULTS.md). There are 12 JobPilot tests and 28 earlier JDMatch tests: **40 passed** in the cloud machine. A real Chromium browser executed local mock form tests; no applicant account or external employer received test submissions. The tests cover known/unknown fields, file upload, success confirmation, ambiguous submission, duplicates, limits, preparation mode, session lock and daily timing.

An unauthenticated live access check is recorded in `validation/live_access.json`. Real discovery, portal selectors, your application answers, authenticated submission and a next-day scheduled run remain unverified. Therefore this is a prototype awaiting account setup and live compatibility validation, not a finished unattended “apply to all jobs” service.

## GitHub and privacy

Code, documentation and sanitized validation evidence are saved to the repository's `jobpilot-agent` branch. Your master resume is unchanged. Runtime sessions, cookies, private answers, database and generated application reports remain local in ignored folders. Upload only the resume/report files you intend to share; never publish browser-session data or account credentials. GitHub Actions was not configured to receive your credentials or submit applications.

## Official API research

Lever's official [Postings API documentation](https://github.com/lever/postings-api#apply-to-a-job-posting) requires an employer administrator's API key for application POST requests; personal applicant credentials are not interchangeable with that key. LinkedIn/Naukri support here is browser-based and conditional, not a claim of an official applicant submission API.
