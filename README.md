# dev-workspace

`dev-workspace` is a curated collection for practical development work involving
CLI tools, scripts, automation, Linux, DevOps, networking, security, and general
software development.

The repository currently provides an organized foundation for future additions.
Tools and examples will be documented as they are added; the directory names
below describe their intended scope and do not imply that implementations already
exist.

## Repository structure

| Path | Intended content |
| --- | --- |
| `bash/` | Bash scripts and shell-oriented utilities |
| `python/` | Python command-line tools and automation |
| `powershell/` | PowerShell scripts and modules |
| `go/` | Go command-line applications and packages |
| `linux/` | Linux-specific commands, configuration examples, and operations notes |
| `linux/windows-compat-commands/` | Linux CLI tools providing functionality inspired by familiar Windows commands (`assoc`, `choice`, `clip`, `pause`, `sfc`, `systeminfo`) |
| `windows/` | Windows-specific commands, configuration examples, and operations notes |
| [`windows/linux-compat-commands/exa/`](windows/linux-compat-commands/exa/) | Linux-inspired file listing for Windows with icons, colors, tree view, and Git status |
| `android/` | Android-specific commands and utilities (e.g. Termux) |
| [`android/termux-commands/`](android/termux-commands/) | Python-based CLI tools for Termux on Android: [`exa`](android/termux-commands/exa/) (modern `ls` replacement) and [`sysinfo`](android/termux-commands/sysinfo/) (`systeminfo` OS/hardware/network report) |
| `docker/` | Dockerfiles, Compose examples, and container tooling |
| `git/` | Git helpers and workflow notes |
| `snippets/` | Small, reusable command and code snippets |
| `docs/` | Longer-form documentation that applies across the repository |
| `experiments/` | Clearly identified exploratory work that is not production-ready |

## Using this repository

Review a file and its documentation before running it. Scripts, commands, and
configuration can have environment-specific effects, particularly when they
involve system administration, networking, security, or containers. Never commit
credentials or sensitive environment details; use sanitized examples instead.

## Contributing

Keep additions focused and place them in the most specific directory. Document
prerequisites, supported platforms, usage, and potentially destructive behavior
alongside each substantial tool. Prefer examples with placeholder values over
real hostnames, addresses, tokens, or credentials.

## License

This project is available under the [MIT License](LICENSE).
