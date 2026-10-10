# JDMatch Resume Agent — how to use it

**Agent name:** JDMatch Resume Agent. This is a Python application with a browser interface and a CLI. It runs on your own computer; GitHub stores the downloadable source and generated examples.

## Download

Open https://github.com/jadonsinghsumit/MyAIAgents and select **Code → Download ZIP**. Extract it and open a terminal in the extracted `MyAIAgents-main` folder. Install Python 3.12 first if needed.

## Windows

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -c requirements.lock -e ".[dev]"
.venv\Scripts\python.exe -m uvicorn ats_agent.web:app --host 127.0.0.1 --port 8765
```

## Linux/macOS

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -c requirements.lock -e '.[dev]'
.venv/bin/python -m uvicorn ats_agent.web:app --host 127.0.0.1 --port 8765
```

Fresh installation is verified on Python 3.12/Linux. Windows/macOS instructions are provided but not independently executed in this cloud environment.

Keep the terminal running. On **your own computer**, type `http://127.0.0.1:8765` into your browser. This address refers to the machine running the application; the cloud instance is not a public hosted agent.

## Required inputs

1. **Company short name:** CISCO, PAN, DELL, etc.
2. **Resume:** upload `resume/profile.json` for your bundled reviewed profile, or your PDF/DOCX/TXT. The structured profile gives the most predictable extraction; review it before applying. Your profile automatically retains your uploaded photo.
3. **Job description:** paste the complete JD, **or** enter one public HTTPS job URL. Login-only or blocked sites need the pasted description.

Select **Analyze and tailor**. It downloads a one-page PDF, editable Word document and match report. No external AI API key is needed. Each run creates a new result.

## Naming and footer

Example: `SUMIT_SINGH_JADAUN_CISCO_2026-10-10_a1b2c3d4.pdf`.

Company, India-local date and unique run ID are included in filenames. A small company/date footer appears on the resume. Earlier files and the master resume are retained. Reports and plain-text/JD files also get unique names.

## Outputs and limits

The internal score is a **keyword/evidence match**, not a score returned by Cisco, LinkedIn, Palo Alto Networks or another ATS vendor. The app highlights missing requirements and required human review. It reorders supported facts and compacts the page; it does not invent experience to force a 90% result. Review employer claims, dates, seniority, qualifications, location and every exported resume before submitting.

Your two real-JD runs are saved at [validation/LATEST.md](validation/LATEST.md). Both yield one-page photo resumes, but the internal scores are below 90%: Cisco 47.2%, Palo Alto Networks 58.1%. This criterion remains unmet; neither is represented as guaranteed to qualify.

Your original approved resume is unchanged in the `resume/` folder. `validation/` contains separate job-specific variants, evidence reports, captured JDs and test records.

## CLI alternative

```bash
.venv/bin/python -m ats_agent.cli --resume resume/profile.json --company CISCO --jd examples/real_jobs/cisco_nexus_dashboard.txt --out outputs/cisco-run-1
```

On Windows replace `.venv/bin/python` with `.venv\Scripts\python.exe`. Use a fresh output directory for each CLI run; the web interface creates unique result folders automatically. For a link, replace `--jd ...` with `--url 'https://…'`.

## Save future results to GitHub

The current agent, examples and reports are committed in this repository. Future local runs remain on your computer until you upload or commit them. After reviewing, use GitHub **Add file → Upload files** to save PDF, Word and report files into an appropriate job folder. Do not upload `.venv/` or private credentials. The agent deliberately does not push every upload automatically or ask for a GitHub token.
