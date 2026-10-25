# daneel

A Claude Code plugin marketplace: the flow shared by phileggel's projects.
`README.md` says what it holds and how a project enables it.

- Nothing here knows one project, and nothing names one: not a skill, script, test,
  changelog, manifest or README. A line that needs a project's name belongs in that
  project, or in a setting the project gives the skill.
- A skill comes here extracted from the projects' copies, with the differences
  between them measured and recorded in its pull request — never written
  generic first.
- A plugin ships every script and doc its skills and agents use, reached from their own
  folder (`${CLAUDE_SKILL_DIR}`), never from the project's checkout; a script measures
  the checkout it runs in, and takes the project's own part from `.claude/daneel.json`.
  It works from a plain checkout too, as CI uses it.
- Every change to a plugin bumps its `version` in `plugin.json` and adds its
  line to `CHANGELOG.md`, saying what a project must do.
- `claude plugin validate .` and `python3 -m unittest discover -s tests` pass before a
  commit; CI runs both. A release is `claude plugin tag plugins/<plugin> --push` on `main`.
- The backlog is GitHub issues (`.github/ISSUE_TEMPLATE/`), never files in git.
