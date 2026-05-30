## 2026-05-20 - [Argument Injection Mitigation in Git Commands]
**Vulnerability:** User-controlled configuration values (like repository URLs or paths) passed directly to `git` subcommands (`ls-remote`, `clone`) via `subprocess.run` are vulnerable to argument injection if they start with a hyphen (e.g., `--upload-pack=malicious_command`).
**Learning:** Even when using lists in `subprocess.run` without `shell=True`, passing untrusted strings that begin with a hyphen to executables can be interpreted as flags, leading to arbitrary code execution or other unintended behavior.
**Prevention:** Always use the `--` separator in subprocess command lists before passing user-provided strings (paths or URLs) as positional arguments to ensure they are interpreted strictly as positional inputs (e.g., `['git', 'clone', '--', auth_url, str(path)]`).

## 2026-05-18 - [Credential Helper Log Leakage Prevention]
**Vulnerability:** The application executes `git` processes with an inline credential helper string (e.g. `credential.helper=!f() { echo username=token; echo password=$TOKEN; }; f`). The `sanitize_token` function only stripped passwords from URLs but left the credential helper string unmodified. If a `subprocess.CalledProcessError` occurs, this raw command is written out in logs/stacktraces.
**Learning:** Hardcoded commands with secrets in shell strings (like credential helpers) represent an often-overlooked path for secret leakage when dealing with process exceptions.
**Prevention:** Ensure `sanitize_token` explicitly scans for and redacts `echo password=...` assignments or any other similar inline secret injection patterns.

## 2024-05-18 - [Command Injection via Unsanitized Shell String Interpolation]
**Vulnerability:** A command injection vulnerability was present when generating default `verify_command`s (`test -d {package_path}`). User-controlled configuration paths were interpolated into shell strings without escaping, allowing arbitrary shell command execution if the path contained characters like `;` or quotes.
**Learning:** Shell strings generated dynamically from configuration values must always be sanitized. `shlex.quote()` is necessary, but it breaks shell-native features like tilde `~` expansion, meaning `os.path.expanduser` must be called *before* escaping the path.
**Prevention:** Use `shlex.quote(os.path.expanduser(path))` for all paths passed into shell command string interpolation.

## 2026-05-20 - [Argument Injection in NPM/NPX Commands]
**Vulnerability:** User-provided npm package names were being passed to `subprocess.run` (and internal wrappers like `run_process` / `run_version_command`) in `npm show`, `npm view`, and `npx` commands without separating positional arguments from flags. This could allow an attacker to inject arbitrary command-line arguments (e.g. `--eval`, `--script-shell`) by providing a malicious package name.
**Learning:** Even when passing arguments as a list to `subprocess.run` (shell=False), positional arguments that start with `-` or `--` will be interpreted as options/flags by the target executable (like npm/npx) unless explicitly separated.
**Prevention:** Always use the `--` separator before passing user-controlled variables as positional arguments to CLI tools (e.g., `npx --yes -- <package_name>` instead of `npx --yes <package_name>`).

## 2024-05-20 - [Argument Injection in System Open Commands]
**Vulnerability:** User-controlled paths were passed directly to `open` (macOS) and `xdg-open` (Linux) via `subprocess.run` without any flag separation or sanitization. If an attacker provided a path starting with a hyphen (e.g., `--help` or more malicious flags), the command would interpret it as an option rather than a path, potentially leading to argument injection or unexpected command execution.
**Learning:** System open commands are susceptible to argument injection just like other CLI tools. However, mitigation strategies vary by OS: `open` accepts the `--` argument separator, whereas `xdg-open` does not support it reliably across all desktop environments.
**Prevention:** For macOS `open`, always use the `--` separator (`subprocess.run(["open", "--", path])`). For Linux `xdg-open`, manually sanitize paths starting with `-` by prepending `./` to force evaluation as a relative file path (`subprocess.run(["xdg-open", f"./{path}" if path.startswith("-") else path])`). Windows `os.startfile` does not parse command-line arguments in this manner and is inherently safe.

## 2026-05-20 - [Arbitrary File Move via Log Parsing Path Traversal]
**Vulnerability:** The application parsed package installation logs for "Installed to <path>" and blindly trusted absolute paths from the output. Since NPM post-install scripts can output arbitrary text, a malicious package could print "Installed to ~/.ssh", tricking the application into moving the user's sensitive directories into the managed skills folder.
**Learning:** Parsing unstructured command output to determine file paths is inherently dangerous if the command's output can be influenced by untrusted parties.
**Prevention:** Always enforce a strict directory jail (e.g., ensuring the parsed path `is_relative_to(staging_base)`) when extracting and manipulating paths from process output logs.

## 2026-05-27 - [Arbitrary Command Execution via Git ext:: Transport Protocol]
**Vulnerability:** User-provided repository URLs are passed to `git clone` and `git ls-remote`. If an attacker provides a URL starting with `ext::` (e.g., `ext::sh -c 'malicious_command'`), Git's `ext` transport protocol will execute the specified shell command.
**Learning:** Git's support for the `ext::` protocol is a well-known command execution vector (similar to CVE-2022-39253). When invoking Git subprocesses against untrusted URLs, it is necessary to disable potentially dangerous features.
**Prevention:** Always add `-c protocol.ext.allow=never` to `git` subprocess commands before the subcommand (e.g., `["git", "-c", "protocol.ext.allow=never", "clone", ...]`) to strictly prevent this transport layer.

## 2024-05-30 - [Secret Leakage via Multiline RegEx Fail-Open]
**Vulnerability:** A regex update attempting to preserve audit log context while redacting secrets in `sanitize_token` failed open on multiline strings. The non-greedy `(.*?)` followed by a lookahead for a command termination string `(?=;\s*\};\s*f|$)` caused the entire match to fail if a newline was encountered before the end-of-string `$`, because `.` in Python does not match newlines by default. This caused the unredacted password to be leaked in plain text.
**Learning:** When writing regex logic to sanitize secrets, a "fail closed" approach should be prioritized. Furthermore, regexes on multiline strings (like command output or logs) are brittle if they rely on the end-of-string character `$` without accounting for newlines (`\r|\n`).
**Prevention:** When using Python regex to redact secrets from text that might contain newlines, ensure lookaheads or match bounds explicitly account for newlines (e.g., `(?=...|\r|\n|$)`) or enable `re.DOTALL`, so that they still match and redact the secret even if the expected suffix is absent or located across a line break.
