# Fieldstone Media : Agentic AI Content Production System
 
**Team:** Group 4
**Client:** Fieldstone Media
 
## Business Problem
 
Fieldstone Media's current content production process is fully manual:
 
```
Researcher → Shared Research Document → Writer → Editor / Fact-Checker → Revision → Publication
```
 
This process is slow and staff-intensive. Multiple human handoffs and editorial back-and-forth increase turnaround time and limit how many clients the agency can serve. The business question this project addresses:
 
> Can Fieldstone Media use an agentic AI workflow to reduce staff-hours and turnaround time per article while maintaining acceptable editorial quality?
 
## Proposed Solution
 
An agentic workflow that automates research, drafting, and quality review, while preserving a human checkpoint for exceptions. The system must demonstrate four required features:
 
1. Parallel agents
2. Critic / reviewer
3. Retry logic
4. Business case (before/after comparison)
## Architecture
 
```
                        Client Brief
                              │
                 ┌────────────┴────────────┐
                 ↓                     	   ↓
        Source Researcher      	Context / Angle
        R-### evidence         	CTX-### guidance
                 │                         │
                 └────────────┬────────────┘
                              ↓
                         Shared State
                 source_research kept separate
                 context_research kept separate
                              │
                              ↓
                            Writer
                              │
                        writer_output
                              │
                              ↓
                            Critic
                       K1–K8 checks
                         PASS / FAIL
                              │
                 ┌────────────┴────────────┐
                 │                     	   │
               PASS                   	 FAIL
                 │                     	   │
                 ↓                     	   ↓
           Final Output         	Orchestrator
                                    decides route
                                   /        	\
                           retry available 	escalate
                                │             	│
                                ↓             	↓
                         Writer Revision 	Human Review
                                │             	│
                                ↓             	↓
                              Critic     	Correct/Approve
                                │             	│
                                └──────→ 	Final Output

```
 
Research is parallelized because the Writer should not produce factual claims before reliable research exists, and source-gathering and context-gathering can safely happen at the same time. Results are merged into shared state before the Writer drafts.
 
## Agents
 
| Agent | Responsibility |
|---|---|
| Source Researcher | Collects factual information, sources, statistics, evidence |
| Context / Angle Researcher | Collects audience info, related context, themes, trends, possible angles |
| Writer | Produces the article draft from shared state |
| Critic / Editor | Evaluates the draft against research and client brief; issues PASS/FAIL |
 
## Team Engineering Roles
 
| Owner | Role | Owns |
|---|---|---|
| Ana Cortez | Orchestrator Engineer | Main workflow, execution order, parallel-agent coordination, shared state, routing PASS/FAIL |
| Dejameir Bagot | Integration Engineer | Research/tool APIs, external data connections, agent-to-agent data compatibility |
| James Paek | Prompt Engineer | Separate system prompts for each agent (Role, Input, Task, Rules, Restrictions, Output Format) |
| Jackie Recendez | Logging & Observability Engineer | Full exchange logging across every run |
| Krystle Baylor | QA / Critic Engineer | Critic logic and quality-assurance testing across all layers |
 
## Shared State
 
All agents read from and write to a common state object, conceptually containing:
 
- `client_brief`
- `research_sources`
- `key_facts`
- `audience_context`
- `writer_draft`
- `critic_verdict`
- `critic_issues`
- `revision_instructions`
- `retry_count`
- `final_status`
The exact technical format is finalized during implementation, but every component must agree on what it receives and returns.
 
## Critic Process
 
The Critic evaluates the Writer's draft against the research packet and client brief on six checks:
 
1. **Factual Grounding** — Are claims supported by supplied research?
2. **Source Fidelity** — Did the Writer accurately represent the source?
3. **Unsupported Claims** — No invented statistics, quotes, dates, names, findings, or attributions.
4. **Client Requirements** — Topic, audience, tone, length, format, required sections.
5. **Internal Consistency** — Does the article contradict itself?
6. **Publication Risk** — Any serious issue that should block publication?
**Critic output structure:**
 
```
VERDICT: PASS or FAIL
ISSUES: What failed
EVIDENCE: What source or requirement proves the failure
REVISION_INSTRUCTIONS: What exactly should the Writer change
SEVERITY: Minor / Major / Critical
RETRY: Yes / No
```
 
## Retry Process
 
```
Writer Draft → Critic → FAIL → Revision Instructions → Writer Revises → Draft 2 → Critic
```
 
- If the revised draft passes, the workflow continues.
- If failures persist past the maximum retry limit, automation stops and the article escalates to a human.
- **Proposed maximum automated retries: 2** (to be confirmed with the instructor/team).
## Human Approval Gate
 
**Recommended model: Exception-Only Approval.**
 
Routine drafts move through the automated Critic and continue on PASS. Human review is triggered when:
 
- Critical problems remain
- Maximum retries are reached
- The Critic cannot confidently approve the article
- High-risk content requires manual review
This preserves human editorial judgment for exceptions while removing routine editing workload — the human checkpoint retained from the original manual process.
 
## Logging
 
Every run records:
 
- Run ID
- Timestamp
- Agent name
- Agent input / output
- Errors
- Critic verdict and issues
- Retry count
- Next action
- Final status
Logs should be complete enough that the team can reconstruct exactly what happened during any run.
 
## Repository Structure
 
```
fieldstone-media-agentic-content/
├── README.md
├── requirements.txt
├── .gitignore
├── .env.example
├── src/
│   ├── main.py
│   ├── state.py
│   ├── agents/
│   │   ├── source_researcher.py
│   │   ├── context_researcher.py
│   │   ├── writer.py
│   │   └── critic.py
│   ├── prompts/
│   │   ├── researcher_prompt.py
│   │   ├── writer_prompt.py
│   │   └── critic_prompt.py
│   ├── workflow/
│   │   ├── orchestrator.py
│   │   └── retry.py
│   ├── integrations/
│   │   └── research_tools.py
│   └── logging/
│       └── logger.py
├── tests/
│   ├── test_critic.py
│   ├── test_retry.py
│   └── test_workflow.py
├── docs/
│   ├── architecture.png
│   ├── before_after.md
│   ├── human_checkpoint.md
│   └── qa_test_plan.md
└── examples/
    └── sample_run.json
```
 
## Installation
 
```bash
git clone <repo-url>
cd fieldstone-media-agentic-content
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # then fill in your real API keys
```
 
> **Security:** Never commit a real `.env` file or API key. `.env` is excluded via `.gitignore`; only `.env.example` (placeholders) is committed.
 
## How to Run the System
 
```bash
python -m src.main
```
 
This runs a client brief through the full pipeline: parallel research → shared state merge → Writer → Critic → retry (if needed) → human gate (if triggered) → final output, with a full log written for the run.
 
## How to Run Tests
 
```bash
pytest tests/
```
 
Tests are organized in layers:
 
1. **Component testing** — each agent in isolation (research returns usable results, Writer returns expected format, Critic returns required fields)
2. **Critic testing** — deliberately correct and incorrect examples (correct facts, incorrect facts, invented quotes, missing client requirements)
3. **Integration testing** — components correctly pass data to each other
4. **Retry testing** — FAIL triggers retry, retry count increases, PASS stops the loop, max retries halt the workflow and escalate
5. **End-to-end testing** — one realistic client brief run through the entire system, checked against the full [Definition of Done](#definition-of-done)
## Known Limitations
 
- Maximum retry count (2) is a starting proposal, not yet confirmed with the instructor.
- Exception-only human approval reduces review volume but means minor issues could reach output before being caught by audit.
- Business-case turnaround/staff-hour figures not yet measured are prototype assumptions, not production data, and should be labeled as such.
- Exact shared-state schema and Critic JSON structure are finalized during implementation and may evolve from what's documented here.
