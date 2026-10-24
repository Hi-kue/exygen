---
title: <% tp.system.prompt("What is the Title of this Note?") %>
date: <% tp.file.creation_date("dddd Do MMMM YYYY HH:mm:ss") %>
modified_date: <% tp.file.last_modified_date("dddd Do MMMM YYYY HH:mm:ss") %>
summary: <% tp.system.prompt("Provide a Summary of the Note (Optional)") %>
uuid:
tags:
    - changelog
    - component-name
index_depth:
is_index?: false
hide:
    - navigation
    - toc
---

# [version or Unreleased] - [YYYY-MM-DD]

## Summary

This changelog, dated [YYYY-MM-DD], covers the changes in [version or Unreleased] of
[component]. It is a structured reference for what was added, changed, and fixed.

### Key Points

- Add one short key point per notable change.

### Added

[New features, endpoints, agents, screens, schemas, or docs pages. Name the files or
contracts involved.]

### Changed/Refactored

[Behavior or interface changes, including anything that breaks a data contract.]

### Fixed

[Bugs fixed and how they were found.]

### Removed

[Optional. Features, files, or dependencies removed.]

### Builds

[Optional. Real release or artifact links only, never placeholders.]
