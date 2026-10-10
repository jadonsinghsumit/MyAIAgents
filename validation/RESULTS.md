# JDMatch validation

28 automated tests passed. Fresh installation and running HTTP upload, matching, one-page PDF, Word/report downloads, and cleanup were verified.

The user reduced acceptance testing from five live openings to the **two supplied real JDs**. Both were processed; neither exceeds 90% on the internal metric. No actual employer ATS scores were obtained.

| Case | Kind | Before | After | PDF pages |
|---|---|---:|---:|---:|
| SAMPLE01 / 01_go_backend | synthetic sample, not a real opening | 100.0% | 100.0% | 1 |
| SAMPLE02 / 02_python_backend | synthetic sample, not a real opening | 100.0% | 100.0% | 1 |
| SAMPLE03 / 03_workflow_security | synthetic sample, not a real opening | 100.0% | 100.0% | 1 |
| SAMPLE04 / 04_cloud_architect | synthetic sample, not a real opening | 41.7% | 41.7% | 1 |
| SAMPLE05 / 05_controller_developer | synthetic sample, not a real opening | 55.6% | 55.6% | 1 |
| CISCO / cisco_nexus_dashboard | real JD supplied by user | 47.2% | 47.2% | 1 |
| PAN / palo_alto_cloud_backend | real JD supplied by user | 58.1% | 58.1% | 1 |

## Real JD limitations

Cisco: missing selected-profile evidence for PostgreSQL, OpenSearch, AI-assisted development, AI prototyping/agents, cluster lifecycle, certificate lifecycle, observability, testing and CI/CD.

Palo Alto Networks: missing selected-profile evidence for distributed systems, data modeling, cloud platforms, SQL/NoSQL, RabbitMQ and testing. Java/Go/Python alternatives are grouped; Go/Python satisfy that group.

Testing is omitted from the selected master resume at the user’s request; the original long resume includes testing experience. A missing label describes the supplied evidence, not proof of an absent skill.

Each real JD was pasted by the user; active vacancy status, location and source-link correspondence were not independently verified. Complete JD snapshots and source metadata are in examples/real_jobs/.

Greenhouse live reads returned network-proxy 403. The supplied LinkedIn job URL could not be resolved, so its content was obtained only through the user’s pasted JD, not through a successful URL fetch. Mocked JobPosting URL extraction is tested; live-site retrieval remains environment-dependent.

No missing experience was borrowed from the web. Results remain below 90% where evidence is missing or unresolved. All files are listed in manifest.json; generated variants retain separate company/date/run-ID names and company/date footers.

The original photo master resume is unchanged. Agent variants for the bundled user profile retain the top-right photo automatically; other profiles can supply a photo through CLI --photo. Repeated runs preserve distinct company/date/run-ID files.

Saved environment install/start/network draft is not publication or a live runtime network change.