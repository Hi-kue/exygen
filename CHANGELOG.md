# Exygen Changelog

<!--NOTE
Use this document to structure commits and massive features 
for each branch that you are working on. Whether you are an
agent or a human being, this should be your scratchpad for
everything. When a PR needs to be made, use this changelog
as a reference for what needs to be presented regarding 
the changes that have been made throughout the branch with
each commit hashs.-->

## Changelogs (Commits)

### Feature: Example Feature Group

- `2026-11-07-example-entry-a1b2c3d`: One-line summary of the change.
  - Detail about what changed and where (e.g. `apps/api/src/exygen_api/`).
  - Detail about why it changed or any behavior impact.

## Changelog Conventions

### Entry Format

Each entry is a list item with the following ID, followed by a one-line summary:

```text
YYYY-MM-DD-[short-abbreviation-text]-[github-hash]
```

- `YYYY-MM-DD`: Date of the commit.
- `[short-abbreviation-text]`: Short kebab-case label for the change (e.g. `api-health-route`).
- `[github-hash]`: Short git commit hash (7 characters) of the commit.

If a single line is not enough to describe the change, add sub list items
beneath the entry with the details.

### Structure

- Group entries under a header per major change or major feature (e.g. `### Feature: Name`,
  `### Refactor: Name`, `### Fix: Name`).
- Minor changes may be listed under a general header such as `### Chores`.
- Keep entries in chronological order within each group.
- Add entries as commits are made so the PR description can be built from this file.
