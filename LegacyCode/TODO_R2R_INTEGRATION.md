# TODO – Integrate Onyx with R2R Document Ingestion

A concise checklist for sending connector output directly to R2R (https://github.com/SciPhi-AI/R2R) instead of, or in addition to, Vespa.

---

## 0. Pre-requisites
- Running Onyx backend (OSS edition is fine).
- R2R instance or SaaS endpoint reachable from the Onyx workers.
- `x-api-key` value provisioned for each tenant / user.

---

## 1. Create an R2R sender
1.  Add new package `backend/onyx/r2r_sender/` with a single class:
    ```python
    class R2RDocumentSender:
        def __init__(self, base_url: str, api_key: str): ...
        def send_batch(self, docs: list[Document]): ...
    ```
    – Build payload **per Document** (concatenate section text; include metadata).
    – POST to `POST /api/documents` with header `x-api-key`.
    – Use `backoff` for retry.

2.  **Optional**: if R2R supports bulk upload, send a single JSON list instead of looping.

---

## 2. Inject sender into the doc-fetching task
1.  Open `backend/onyx/background/indexing/run_docfetching.py`.
2.  Near the top of the file, instantiate once per Celery task when the flag is enabled:
    ```python
    if os.getenv("ONYX_EXPORT_R2R", "false").lower() == "true":
        r2r_sender = R2RDocumentSender(
            base_url=os.environ["R2R_BASE_URL"],
            api_key =os.environ["R2R_API_KEY"],
        )
    ```
3.  In the main processing loop
    ```python
    for document_batch, failure, next_checkpoint in connector_runner.run(checkpoint):
        if document_batch and os.getenv("ONYX_EXPORT_R2R", "false").lower() == "true":
            r2r_sender.send_batch(document_batch)
    ```
4.  Decide whether to
    - **Mirror**: keep existing call to `index_doc_batch_with_handler(...)` (pushes to Vespa **and** R2R).
    - **Replace**: skip the chunking/indexing call when `ONYX_EXPORT_R2R` is set.

---

## 3. Expose API key in the UI / DB
- Add new `CredentialType.R2R_API` (or reuse generic secret).
- Extend settings/credentials form in `web/` to capture `R2R_BASE_URL` + `x-api-key`.
- During task start-up, fetch the credential instead of `os.environ`.

---

## 4. (Alternative) Implement as DocumentIndex instead
If you prefer to leave the pipeline unchanged and intercept at the “chunk” level:
1.  Create `backend/onyx/document_index/r2r/index.py` implementing `DocumentIndex`, `Indexable`.
2.  Return this class from `document_index/factory.py` when `ONYX_INDEX_BACKEND=r2r`.
3.  This path retains chunking and Vespa back-off logic but requires handling chunks on the R2R side.

---

## 5. Checkpoint & progress tracking
Nothing to change – `checkpointing_utils.save_checkpoint()` and `ConnectorCheckpoint` remain untouched.  The sender runs **before** checkpoint save logic, so retries will re-send the batch automatically if the task fails mid-flight.

---

## 6. Testing checklist
- [ ] Run a poll-type connector (e.g. Slack) with `ONYX_EXPORT_R2R=true` and verify documents appear in R2R.
- [ ] Kill the worker mid-run; restart; ensure checkpoint resumes and R2R sees no duplicates (R2R is idempotent on `id`).
- [ ] Toggle flag off to confirm normal Vespa indexing still works.

---

## 7. Future ideas
- Composite “MirrorIndex” that writes to both Vespa and R2R via `DocumentIndex` abstraction.
- Per-tenant `R2R_API_KEY` mapping stored in Postgres so multi-tenant export targets different buckets.
- Hook export into **doc-delete** and **update** paths once R2R adds corresponding endpoints. 