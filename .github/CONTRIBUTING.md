# Contributing

Add one formula or cask per pull request. Use a concise Conventional Commit title,
such as `feat: add example formula` or `chore(example): update to 1.2.3`.

Before opening a pull request:

1. Generate the Ruby file with the `homebrew-add` scaffolder from
   `homebrew-tap-skills`; do not hand-write it and do not use `brew create`.
2. Review inferred metadata, system dependencies, artifact names, and test blocks.
3. Run the relevant Homebrew audit and install/test checks.
4. Run `mise run generate-readme`.
5. Run `mise install` and `mise run check`.

Include the commands and results in the pull request's verification section.

## Automated pull requests

The update and boilerplate-drift workflows open pull requests with the repository
secret `WORKFLOW_TOKEN` if present, falling back to `GITHUB_TOKEN`. GitHub does
not start workflows for actions performed by `GITHUB_TOKEN`, so maintainers run
the `brew test-bot` workflow manually via `workflow_dispatch` on the update branch
before merging (tap-syntax and cask audit; the bottle build runs once pull
request checks start), or close and reopen such a pull request (or push to its
branch), or configure `WORKFLOW_TOKEN` to start everything automatically.
