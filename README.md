# RunLab

**User-facing Jupyter Notebook/JupyterLab workbench for reproducible AI-assisted research.**

`RunLab` (`run-lab`) is a proposed local-first reproducible research workbench for AI-assisted literature review, notebook execution, evidence packets, rendered reports, and replayable research workflows.

The project restores the original product center:

> The report is not the durable object. The evidence-backed run packet is.

RunLab is meant to sit beside the NeuML ecosystem and make `txtai`-backed research runs inspectable from request to report. It does not replace `txtai`, `paperetl`, `paperai`, Jupyter, notebooks, peer review, or scientific judgment. It gives researchers a user-facing workspace where official notebook runs can produce structured evidence, not just polished output.

Status: proposed product/research concept. Not an existing official NeuML product unless adopted by NeuML.

---

## Product description

RunLab is a Jupyter-facing reproducible research interface for AI-assisted science.

It helps a researcher:

- define a research question or query job;
- select an explicit `txtai` or local retrieval index;
- run an official parameterized notebook template;
- preserve the executed notebook;
- record retrievals, citations, context, environment details, artifacts, and logs;
- render a human-readable report;
- package the whole run as an evidence-backed research object;
- inspect or replay the run under documented limits.

RunLab should eventually feel like a research workbench inside or beside Jupyter Notebook/JupyterLab, not just a backend command-line tool.

---

## Why RunLab?

AI-assisted research tools can produce polished summaries, literature tables, notebook outputs, and reports quickly. But a polished report is not durable research evidence by itself.

A trustworthy research workflow should preserve the evidence path:

- What question was asked?
- What corpus or index was searched?
- What retrieval settings were used?
- What sources and passages were retrieved?
- What citations appeared in the report?
- What notebook template ran?
- What parameters were passed into the notebook?
- What environment produced the output?
- What artifacts were generated?
- Can another person inspect or replay the run?
- What has the system not proven?

RunLab makes that path a first-class output.

---

## Relationship to the project stack

```text
Evidence Packet Core
  -> low-level evidence records, manifests, hashes, replay metadata, verifier

RunLab
  -> user-facing Jupyter Notebook/JupyterLab reproducible research workbench

TraceLab
  -> future adapter-aware instrumented-research evidence orchestrator
```

RunLab is the user-facing notebook layer. It should use the evidence packet core underneath it and may later consume TraceLab evidence packets from instrumented research workflows.

---

## Product fit with the NeuML stack

```text
paperetl   -> parse and structure scientific papers
txtai      -> index, search, retrieve, and power RAG workflows
paperai    -> generate literature workflows, answer tables, and reports
RunLab     -> run notebooks, record evidence, render reports, verify packets, and support replay
TraceLab   -> capture lab-run evidence from instrumented workflows for later search/reporting
```

RunLab does not replace `txtai`, `paperetl`, or `paperai`.

It adds a reproducible-research workbench layer around them.

| Project | Existing role | Where RunLab fits |
|---|---|---|
| `txtai` | Semantic search, embeddings, RAG, workflows, agents, APIs, and multimodal indexing | Supplies retrieval events, index references, query metadata, context records, and possible workflow hooks |
| `paperetl` | ETL for medical and scientific papers | Supplies structured source metadata, identifiers, hashes, and citation locators |
| `paperai` | AI-assisted search and reporting over scientific papers | Supplies or consumes generated reports, answer tables, and paper-level artifacts |
| Evidence Packet Core | Low-level evidence/provenance records | Provides the packet schema, artifact manifest, authority vocabulary, replay metadata, and verifier |
| RunLab | User-facing reproducible research workbench | Runs official notebooks and packages the evidence-backed run |
| TraceLab | Instrumented research evidence layer | Later provides lab evidence packets that RunLab and PaperAI-style reports can cite |

---

## What RunLab is

RunLab is:

- a local-first reproducible research workbench;
- a user-facing Jupyter Notebook/JupyterLab interface direction;
- a notebook template runner;
- an evidence-backed run packet generator;
- a report renderer;
- a replay/inspection surface;
- a bridge between `txtai` retrieval, notebooks, reports, and durable evidence records.

---

## What RunLab is not

RunLab is not:

- a replacement for Jupyter;
- a replacement for `txtai`, `paperetl`, or `paperai`;
- a general RAG framework;
- a model server;
- a hidden local model downloader;
- a citation manager;
- a lab-control framework;
- an autonomous agent system;
- a scientific validator;
- a peer-review substitute;
- a source-control settlement tool.

RunLab can support evidence and reproducibility. It does not prove scientific truth by default.

---

## First runnable slice

The first release should stay narrow:

```text
LocalGPT Notebook Evidence Runner v0.1
```

One official notebook.  
One explicit query job.  
One explicit `txtai` or local index reference.  
One rendered report.  
One complete evidence packet.

The first slice can be CLI-driven while preserving the future JupyterLab interface boundary. The product should not pretend to have a full UI before the evidence path is proven.

---

## Core workflow

```text
1. Create or inspect workspace
2. Add query job
3. Select explicit txtai/local index reference
4. Run official parameterized notebook template
5. Produce executed notebook
6. Write retrieval record
7. Write source citations
8. Write context pack
9. Write notebook run record
10. Write environment report
11. Render HTML/Markdown report
12. Write replay manifest
13. Verify artifact presence/schema shape
14. Inspect the evidence-backed run packet
```

---

## What a run produces

A typical official run produces:

```text
runs/<run-id>/
  inputs/
    query_job.json
    index_reference.json
  parameters/
    papermill_parameters.json
  executed/
    literature_evidence_runner.executed.ipynb
  records/
    retrieval_record.json
    source_citations.json
    notebook_run_record.json
    environment_report.json
    replay_manifest.json
    verification_report.json
    artifact_manifest.json
  context/
    context_pack.md
  reports/
    rendered_report.html
    rendered_report.md
  logs/
    run.log
```

---

## Evidence packet artifacts

| Artifact | Purpose |
|---|---|
| `query_job.json` | Captures the research question, query text, filters, output request, citation mode, and result limits. |
| `index_reference.json` | Captures the selected `txtai` or local index/corpus reference. |
| `papermill_parameters.json` | Captures parameters passed into the notebook run. |
| `executed_notebook.ipynb` | Preserves the notebook actually executed. |
| `retrieval_record.json` | Records query, backend, retrieval configuration, ranked results, scores, source IDs, and warnings. |
| `source_citations.json` | Links report citations, claims, or sections to sources and retrieval records. |
| `context_pack.md` | Gives a human-readable bridge from retrieved sources to report synthesis. |
| `notebook_run_record.json` | Records template path, template hash, execution status, output paths, and authority flags. |
| `environment_report.json` | Records Python/kernel/package/runtime/resource posture without dumping secrets. |
| `rendered_report.html` / `rendered_report.md` | Human-facing report output. |
| `replay_manifest.json` | Lists inputs, artifacts, hashes, limitations, and replay hints. |
| `verification_report.json` | Mechanical artifact/schema/path/flag check result. |
| `artifact_manifest.json` | File inventory with roles and hashes. |

---

## Jupyter workspace model

RunLab should support a notebook workspace with clear authority boundaries.

| Area | Purpose | Authority posture |
|---|---|---|
| `scratch/` | Free exploration | Never authoritative; not eligible for official evidence runs |
| `exploration/` | Research development | Useful but not official |
| `templates/` | Parameterized notebook templates | Eligible for official runs and Jupytext pairing |
| `official/` | Accepted evidence notebooks | Replay candidates; later nbval candidates |
| `reports/` | Report-focused notebooks and rendered outputs | Human-facing output, not validation authority |

Scratch notebooks can inspire official templates, but they should not become official evidence by path alone.

---

## Future JupyterLab interface

After the first evidence path is stable, RunLab should grow toward a JupyterLab extension or companion UI with focused panels:

| Panel | Purpose |
|---|---|
| Run Queue | List pending, completed, failed, and replayable research runs |
| Query Job | Edit or inspect the research question, filters, and retrieval settings |
| Index Reference | Show the explicit local/`txtai` index or corpus used |
| Evidence Packet | Inspect required records, missing files, hashes, and warnings |
| Sources and Citations | View retrieved passages, citation links, source IDs, and support status |
| Notebook Run | Show template path, executed notebook, parameters, and execution status |
| Environment | Show package/kernel/runtime posture without exposing secrets |
| Report Preview | Render HTML/Markdown report output |
| Replay | Show replay manifest, limitations, and replay command hints |

The UI should make the run understandable without hiding the underlying files.

---

## Public CLI sketch

```bash
run-lab init ./research-evidence

run-lab inspect

run-lab run \
  --query-job jobs/rag_literature_demo.json \
  --template notebooks/templates/literature_evidence_runner.ipynb \
  --index indexes/local_txtai_demo_index.json \
  --output-prefix rag_literature_demo \
  --render html

run-lab verify runs/rag_literature_demo/

run-lab replay runs/rag_literature_demo/records/replay_manifest.json

run-lab render runs/rag_literature_demo/ --format html
```

Suggested Python import name:

```python
import run_lab
```

---

## Authority boundaries

RunLab can produce evidence.  
RunLab can support reproducibility.  
RunLab can mechanically verify artifact shape.  
RunLab does not prove scientific truth by default.

Default authority flags should remain conservative:

```json
{
  "correctness_proven": false,
  "repo_mutated": false,
  "state_promoted": false,
  "source_control_touched": false
}
```

A complete run can be reproducible and still be scientifically wrong. That is why the workbench separates:

| Concept | Meaning |
|---|---|
| Evidence | Records of what was asked, retrieved, cited, executed, rendered, and packaged |
| Reproducibility | Ability to inspect or rerun under documented conditions |
| Verification | Mechanical checks that files exist, JSON parses, fields are present, and hashes/paths align |
| Validation | Domain-level judgment that research claims are scientifically correct |
| Promotion | Human or institutional acceptance of a result as durable knowledge |

---

## v0.1 non-goals

The first release should not include:

- broad PDF/GROBID ingestion;
- large corpus ingestion;
- hidden local LLM downloads;
- `txtai[all]` as a default dependency;
- txtai agents/workflow orchestration by default;
- Docker-first setup;
- full JupyterHub/JupyterLite deployment;
- Snakemake/Nextflow/CWL;
- DVC/DataLad as a required dependency;
- RO-Crate as a binding export requirement;
- automatic `paperetl` execution;
- automatic `paperai` execution;
- source-control mutation;
- lab control;
- scientific validation;
- institutional promotion.

---

## Later integrations

After the v0.1 evidence packet is proven, RunLab can grow toward:

- JupyterLab extension or companion interface;
- bounded `paperetl` source-ingestion records;
- `paperai` report import/wrapping;
- Quarto-backed report rendering;
- RO-Crate export;
- nbval checks for official notebooks only;
- optional DVC/DataLad compatibility;
- TraceLab evidence packet consumption from instrumented workflows.

---

## Demo promise

After a demo run, a user should be able to say:

> I can read the report, inspect the sources, see what notebook ran, see the environment posture, open the evidence packet, and understand what the system did and did not prove.

---

## Suggested repository layout

```text
run-lab/
  README.md
  pyproject.toml
  LICENSE
  CHANGELOG.md

  src/
    run_lab/
      __init__.py
      cli.py
      workspace.py
      jobs.py
      notebook_runner.py
      render.py
      verify.py
      evidence_bridge.py
      errors.py

  notebooks/
    templates/
      literature_evidence_runner.ipynb
      literature_evidence_runner.py

  examples/
    local_txtai_demo/
      jobs/
        rag_literature_demo.json
      indexes/
        local_txtai_demo_index.json

  docs/
    jupyter_workspace_model.md
    evidence_run_model.md
    notebook_policy.md
    neuML_stack_fit.md

  tests/
    test_workspace_init.py
    test_run_lab_cli.py
    test_notebook_run_record.py
    test_artifact_manifest.py
    test_replay_manifest.py
    test_authority_flags.py
```

---

## Status

Planning/design draft for a proposed RunLab project aligned with the NeuML product family.

No official NeuML endorsement or release is implied unless adopted by NeuML.

No source-control mutation. No hardware control. No scientific truth claims.

---

## Further reading

- NeuML: https://neuml.com/
- txtai tutorials: https://neuml.hashnode.dev/series/txtai-tutorial
- txtai: https://github.com/neuml/txtai
- paperetl: https://github.com/neuml/paperetl
- paperai: https://github.com/neuml/paperai
- Papermill: https://papermill.readthedocs.io/
- Jupytext: https://jupytext.readthedocs.io/
- JupyterLab: https://jupyterlab.readthedocs.io/
- Quarto: https://quarto.org/
- RO-Crate: https://www.researchobject.org/ro-crate/
- FAIR4RS: https://www.nature.com/articles/s41597-022-01710-x
