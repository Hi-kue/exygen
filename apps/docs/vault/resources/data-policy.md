---
title: Data Policy
date: Saturday 24th October 2026 18:40:00
modified_date: Tuesday 3rd November 2026 12:40:00
summary: Rules for source exams, permissions, storage, and deletion in Exygen. Stub that records the blueprint rules until policies are finalized.
tags:
    - data-policy
    - privacy
---

# Data Policy

## Summary

This page records how Exygen handles source exams and course materials. The rules below come from `.agents/index.md` (sections 3 and 10). Storage and deletion behavior is not yet documented because it is not yet decided.

> **Status**: Stub. Fill in the open items below once the implementation settles them. Do not state behavior the code does not have.

### Key Points

- Use only authorized or original synthetic exams. University affiliation or public availability does not grant permission to redistribute an exam.
- McGill source documents have unconfirmed permission, so use the synthetic fixtures first.
- Never commit uploaded exams, student data, API keys, or confidential institutional files.
- Enforce upload size and type limits, and keep retention minimal.
- `ClefClient` sends the text it classifies to Cloudflare Workers AI when `CF_ACCOUNT_ID` and `CF_AUTH_TOKEN` are set, and the Classifier uses it for tagging. Cloudflare states that it does not train models on Workers AI content ([data usage](https://developers.cloudflare.com/workers-ai/platform/data-usage/)).
- The Classifier prompt includes the text of each source page, and the Synthesizer and Critic prompts include the raw text of the anchor question. The LLM provider receives all of them. With the `openrouter` provider, this text goes to OpenRouter and the model it routes to.
- Figures from source documents, and pages with almost no text, are sent as images to the vision model set by `AGENT_VISION_MODEL` through OpenRouter. Only the resulting text stays in the graph state, and it is labeled as model-generated.
- When `LANGFUSE_IS_TELEMETRY_ENABLED` is true and the Langfuse keys are set, graph runs send the full LLM prompts, the responses, and the graph state to Langfuse, so source exam text is stored there. Secrets are masked and each value is cut at 250,000 characters, but the exam text itself is not removed. Only enable tracing for documents that may be stored in the configured Langfuse project.
- Tracing also stores the images sent to the vision model. The Langfuse SDK uploads each image to Langfuse media storage before masking runs. Masking then turns the reference in the trace into a placeholder string, so the images do not show in the trace, but they are still stored. This was confirmed on 2026-11-03 by looking up an exam's figures in the Langfuse media API.

## Planned Production Hosting

The [Deployment](../architecture.md#deployment) section describes planned infrastructure that is not deployed. It affects this policy as follows:

- Persistent records would live in PostgreSQL on `db-01`, on self-hosted infrastructure. The team would be responsible for access control, encryption, and deletion.
- Deletion and retention rules must also cover backups, which are stored away from the database VM.
- Sandbox VMs must not receive source documents, secrets, or database access. A job receives only the code and test cases it runs.
- Centralized logs must not contain secrets, exam text, or personal data.

## Open Items

- Storage location for uploaded documents and generated exports. PostgreSQL on `db-01` is planned for records, and the location of files is not decided.
- Encryption at rest for `db-01`, uploaded files, and backups.
- Deletion and retention behavior, including backups, Langfuse traces, and Langfuse media. The placeholder in the trace does not link to the stored image, so deleting one is not straightforward.
- Whether figure images should reach Langfuse at all. Nothing prevents it today.
- Permission acknowledgment wording shown at upload.
- Per-source license and permission inventory.
- A check that only documents with confirmed permission are sent to Cloudflare, OpenRouter, or Langfuse. Nothing enforces this yet. `--permission` on the `run` command records what the caller states.
