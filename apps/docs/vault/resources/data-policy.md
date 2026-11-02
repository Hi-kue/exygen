---
title: Data Policy
date: Saturday 24th October 2026 18:40:00
modified_date: Sunday 1st November 2026 16:20:00
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
- `ClefClient` sends the text it classifies to Cloudflare Workers AI. Nothing calls it yet, and the Classifier is planned to use it. Cloudflare states that it does not train models on Workers AI content ([data usage](https://developers.cloudflare.com/workers-ai/platform/data-usage/)). The text is not written to Langfuse traces.
- The Synthesizer prompt includes the raw text of the anchor question, and the LLM provider receives it. With the `openrouter` provider, this text goes to OpenRouter and the model it routes to.

## Planned Production Hosting

The [Deployment](../architecture.md#deployment) section describes planned infrastructure that is not deployed. It affects this policy as follows:

- Persistent records would live in PostgreSQL on `db-01`, on self-hosted infrastructure. The team would be responsible for access control, encryption, and deletion.
- Deletion and retention rules must also cover backups, which are stored away from the database VM.
- Sandbox VMs must not receive source documents, secrets, or database access. A job receives only the code and test cases it runs.
- Centralized logs must not contain secrets, exam text, or personal data.

## Open Items

- Storage location for uploaded documents and generated exports. PostgreSQL on `db-01` is planned for records, and the location of files is not decided.
- Encryption at rest for `db-01`, uploaded files, and backups.
- Deletion and retention behavior, including backups.
- Permission acknowledgment wording shown at upload.
- Per-source license and permission inventory.
- A check that only documents with confirmed permission are sent to Cloudflare. The Clef client does not enforce this yet.
