# Contribution guidelines

Contributing to this project should be as easy and transparent as possible, whether it's:

- Reporting a bug
- Discussing the current state of the code
- Submitting a fix
- Proposing new features

## GitHub is used for everything

GitHub is used to host code, to track issues and feature requests, as well as accept pull requests.

Pull requests are the best way to propose changes to the codebase.

1. Fork the repo and create your branch from `main`.
2. Run `script/setup/bootstrap` to install dependencies and pre-commit hooks.
3. If you've changed something, update the documentation.
4. Make sure your code passes all checks (using `script/check` for linting and type checking).
5. Test your contribution.
6. Issue that pull request, with a [Conventional Commit](https://www.conventionalcommits.org/) title (see below).

## Pull request titles and releases

Pull requests are squash-merged, so the PR title becomes the commit message on `main`. [release-please](https://github.com/googleapis/release-please) builds releases and the changelog from those commit messages, so **the PR title must be a Conventional Commit**:

| Title prefix                                   | Release               |
| ---------------------------------------------- | --------------------- |
| `fix:` (or `perf:`)                            | Patch (1.8.1 → 1.8.2) |
| `feat:`                                        | Minor (1.8.1 → 1.9.0) |
| Breaking change (`feat!:`, `fix!:`, ...)       | Major (1.8.1 → 2.0.0) |
| `chore:`, `ci:`, `docs:`, `test:`, `refactor:` | No release            |

For example: `fix: handle empty hourly usage data` or `feat: add weekly usage sensor`.

## Any contributions you make will be under the Apache 2.0 License

In short, when you submit code changes, your submissions are understood to be under the same [Apache License 2.0](LICENSE) that covers the project. Feel free to contact the maintainers if that's a concern.

## Report bugs using GitHub's [issues](https://github.com/zestysoft/sensus_analytics_integration/issues)

GitHub issues are used to track public bugs.
Report a bug by [opening a new issue](https://github.com/zestysoft/sensus_analytics_integration/issues/new/choose); it's that easy!

## Write bug reports with detail, background, and sample code

**Great Bug Reports** tend to have:

- A quick summary and/or background
- Steps to reproduce
  - Be specific!
  - Give sample code if you can.
- What you expected would happen
- What actually happens
- Notes (possibly including why you think this might be happening, or stuff you tried that didn't work)

People _love_ thorough bug reports. I'm not even kidding.

## Use a Consistent Coding Style

This project uses:

- [Ruff](https://github.com/astral-sh/ruff) for linting and formatting
- [Pyright](https://github.com/microsoft/pyright) for type checking

Run `script/check` to lint and type-check your code before submitting, or `script/lint` to auto-format and fix linting issues.

**Local validation:** Run `script/hassfest` to validate your integration against Home Assistant's quality standards using the official validation tools. This checks manifest.json, translations, services.yaml (service action definitions), and integration structure locally before pushing to GitHub.

## GitHub Copilot Support

This project includes [prompt files](./.github/prompts/) to help you work more efficiently with GitHub Copilot. These reusable templates provide context and requirements for common tasks:

- **Add Action** - Add a service action with validation
- **Add Config Option** - Add configuration options to flows
- **Add Entity Platform** - Add a new entity platform
- **Add Entity to Device** - Expand device capabilities
- **Add New Sensor** - Create sensors with proper structure
- **Create ADR** - Record an architectural decision
- **Create Implementation Plan** - Plan a larger change before coding
- **Debug Coordinator Issue** - Diagnose data update problems
- **Review Integration** - Review the integration against Home Assistant standards
- **Update Translations** - Manage translation strings

**Example usage in Copilot Chat:**

```text
#file:Add New Sensor.prompt.md Add a temperature sensor
```

See the prompt files in `.github/prompts/` for details on using these templates.

## Code Quality

This integration follows Home Assistant's [integration quality standards](https://developers.home-assistant.io/docs/core/integration-quality-scale/) as best practices. The code includes:

- ✅ Comprehensive docstrings with links to official documentation
- ✅ Full type hints for better IDE support
- ✅ Config flow with reauthentication support
- ✅ Proper error handling and entity unavailability
- ✅ Coordinator pattern for efficient data fetching

## Test your code modification

This project comes with a complete development environment in a container, easy to launch
if you use Visual Studio Code. With this container you will have a standalone
Home Assistant instance running and already configured with the included
[`configuration.yaml`](./config/configuration.yaml) file.

You can also run tests using `script/test` to ensure your changes don't break existing functionality.

## License

By contributing, you agree that your contributions will be licensed under its [Apache License 2.0](LICENSE).
