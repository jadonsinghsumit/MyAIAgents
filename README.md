# JDMatch Resume Agent

Start with the [step-by-step access guide](QUICKSTART.md) and [latest Cisco/PAN resumes](validation/LATEST.md).

Accept a **pasted job description** or **public job link**, compare it with your resume, and export a tailored **one-page PDF**, editable Word document, and evidence report. Includes a local web interface and command-line workflow. Runs without an LLM API key.

**This is a transparent, rule-based matching agent. It does not call an employer ATS or guarantee a score above 90%, an interview, or an offer.** It never invents missing cloud experience, certifications, employers, dates, or metrics. A job description is data, not instructions to the agent.

## Validation status

- 28 automated tests passed in Python 3.12/Linux, including five complete synthetic JD workflows, PDF/DOCX input, matching, missing skills, unrecognized requirements, link extraction with a mocked public page, URL safety and web downloads.
- A real local HTTP request exercised resume upload → analysis → PDF/Word/report downloads; PDF verified as one page.
- Five synthetic JDs produced one-page PDFs. Three internally matched 100%; the cloud-architect and controller samples matched 41.7% and 55.6%, respectively. Unsupported requirements were reported rather than fabricated.
- **Two user-provided real JDs were tested: Cisco Nexus Dashboard infrastructure at 47.2% and Palo Alto Networks cloud backend at 58.1% internal match; the user’s revised two-JD acceptance runs are complete, but the above-90% goal is NOT achieved.** Live Greenhouse API requests returned `403 Forbidden` from this cloud environment's network proxy. No synthetic example is presented as a real vacancy. The network-domain draft is saved but requires environment settings review/save/publication, or pasted JDs work without network access. The user reduced acceptance testing to the two supplied descriptions.
- See [validation results](validation/RESULTS.md). This is a tested implementation with live-opening validation outstanding, not a claim that the requested real-world acceptance criterion has passed.

## Install

Clone this repository onto your computer and enter its directory. Python 3.11+ is required; dependency constraints and fresh setup are tested on Python 3.12/Linux. Windows/macOS require an independent install check.

```bash
git clone https://github.com/jadonsinghsumit/MyAIAgents.git
cd MyAIAgents
./scripts/setup.sh
```

The script creates `.venv`, installs the package with the tested version constraints, and runs tests. It is safe to rerun and does not change the master resume. On Windows, create a virtual environment with `py -m venv .venv` and use `.venv\Scripts\python.exe -m pip install -c requirements.lock -e ".[dev]"`.

## Browser interface on your own computer

```bash
.venv/bin/python -m uvicorn ats_agent.web:app --host 127.0.0.1 --port 8765
```

Open your browser at loopback port 8765 on your own machine. Enter the company short name (e.g. CISCO/PAN), upload your resume (or `resume/profile.json`), paste the complete JD or enter a public HTTPS job link, and select **Analyze and tailor**. Download PDF, Word and the report from the result. The cloud-onboarding chat does not provide a public preview of this local service.

Use it as a single-user local application. Do not expose it on a public interface without authentication, retention controls and deployment hardening. Uploaded resumes are processed locally; only the public job URL is fetched over the network. No resume is sent to a job site, and no job applications or messages are submitted. Results are stored in a temporary folder and deleted on a normal shutdown, or through `DELETE /results/{id}`. A crash may leave temporary files for local cleanup.

## CLI

```bash
.venv/bin/python -m ats_agent.cli \
  --resume resume/profile.json \
  --company CISCO \
  --jd examples/jobs/01_go_backend.txt \
  --out outputs/go-example
```

For a public link, replace `--jd ...` with `--url 'https://job-boards.greenhouse.io/COMPANY/jobs/JOB_ID'`. Greenhouse links use the public posting API; other sites prefer JobPosting JSON-LD when available. Review the extracted JD: navigation, partial pages, login gates or client-rendered pages can make extraction incomplete. Paste the JD when retrieval fails. No authentication or bot-protection bypass is attempted.

Your bundled profile retains your existing top-right photo automatically. For other profiles, supply a photo with `--photo path/to/photo.jpg`. Your original photo master resume is preserved. Word pagination depends on fonts and Word version; the **PDF** is the verified one-page artifact.

Each filename includes your name, company short name, India-local date, and a unique run ID. The resume footer also shows the company/date. Report and text filenames are unique too. Output directory must be empty. Each job should get a separate directory; neither the master profile nor the original resume is overwritten.

## Resume input and review

Your reviewed profile is at [resume/profile.json](resume/profile.json). It contains the resume claims you provided in this conversation; it is not independently verified. Edit it only when you have truthful additional experience. Do not insert job requirements into employment history merely to improve a score.

PDF/DOCX/TXT input is supported for resumes with standard `PROFESSIONAL SUMMARY`, `TECHNICAL SKILLS`, `PROFESSIONAL EXPERIENCE`, and `EDUCATION` sections and recognizable month/year employment headings. PDF line extraction and arbitrary layouts can be imperfect; inspect `source_profile` in the report before applying. Unknown structures fail with guidance instead of inventing employment. For any other resume, manually prepare and review a JSON profile using the supplied structure. Scanned PDFs require OCR elsewhere.

## How the score works

`100 × covered requirement weights / all detected requirement weights`.

- Required terms weigh 3, general terms 2, preferred terms 1.
- Aliases include Go/Golang, Kubernetes/k8s, Protocol Buffers/Protobuf, OpenID Connect/OIDC.
- Support must come from source skills or employment bullets; an aspirational headline alone earns no credit.
- After tailoring, credit also requires the term's equivalent to be present in **extracted PDF text**.
- The internal target is **strictly greater than 90%**, requires at least five detected terms and no unresolved requirement lines.
- Unrecognized required wording, compound requirements, years, degrees, location and other conditions trigger human review. A visible 100% keyword score can still have status `needs_review_or_missing_evidence`.

This finite vocabulary is **not an exhaustive semantic or competency assessment**. It cannot verify depth, years per technology, a certification, clearance, work authorization, architecture scope, business impact, or every unknown skill. Read the original JD and the evidence report; do not treat the percentage as a vendor ATS result.

## Tailoring and stopping rules

1. Extract supported facts and JD terms; show requirement/evidence rows.
2. Reorder existing bullets by relevance; keep the Atlas Python framework bullet at the end of its employer section.
3. Prioritize already-supported skill names and bold relevant technologies.
4. Render and inspect PDF text and page count.
5. If the document is too long, make up to four bounded compacting passes, recording removed bullets and re-scoring the actual output.
6. Stop when one page fits. If evidence remains missing, report it; repeating the same words does not improve support. If readable one-page output cannot be produced, fail explicitly rather than publishing an oversized or tiny-font document.

Because aliases are recognized before tailoring, improved wording and ordering may leave the numerical score unchanged. The agent does not manufacture a rising score to make its iterations look successful. A truthful master already covering a sample JD can score 100% before and after.

## Run verification

```bash
.venv/bin/python -m pytest -q
```

The `examples/jobs/` files are explicitly **synthetic samples**, not current job advertisements. The `validation/` folder contains sample tailored resumes and reports so you can inspect output. Real vacancies must be captured with source URL/JD and retrieval date before claiming live-opening validation.
