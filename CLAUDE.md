# daneel

A Claude Code plugin marketplace: the flow shared by phileggel's projects.
`README.md` says what it holds and how a project enables it.

- Nothing here knows one project. A line naming folioneer, PatientManager or a
  game belongs in that project, or in a setting the project gives the skill.
- A skill comes here extracted from the projects' copies, with the differences
  between them measured and recorded in its pull request — never written
  generic first.
- Every change to a plugin bumps its `version` in `plugin.json` and adds its
  line to `CHANGELOG.md`, saying what a project must do.
- `claude plugin validate .` passes before a commit; CI runs it too.
- The backlog is GitHub issues (`.github/ISSUE_TEMPLATE/`), never files in git.
