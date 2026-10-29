---
title: Data Policy
date: Saturday 24th October 2026 18:40:00
modified_date: Saturday 24th October 2026 18:40:00
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
- The Classifier sends question text to Cloudflare Workers AI (Clef) for classification. Cloudflare states that it does not train models on Workers AI content ([data usage](https://developers.cloudflare.com/workers-ai/platform/data-usage/)). The text is not written to Langfuse traces.

## Open Items

- Storage location for uploaded documents and generated exams.
- Deletion and retention behavior.
- Permission acknowledgment wording shown at upload.
- Per-source license and permission inventory.
- A check that only documents with confirmed permission are sent to Cloudflare. The Clef client does not enforce this yet.
