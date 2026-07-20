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
## 2025-06-15 - [Critical] Greedy Regex in Secret Redaction Allows Multiline Data Loss and Leakage
**Vulnerability:** The `sanitize_token` function used a greedy `.*` regex match for `echo password=`, which failed to correctly bound redaction, potentially leaking secrets if line boundaries failed or causing log data loss by stripping massive portions of text.
**Learning:** When using Python regex to redact secrets from multiline or unstructured text, greedy matches (`.*`) without newline/boundary constraints (`\r`, `\n`) or escape-aware logic fail catastrophically in logs.
**Prevention:** Always use explicit matching of known token formats (e.g., GitHub tokens), and for unstructured strings like `echo password=`, use safe escape-aware patterns bounded strictly to quotes or spaces.

## 2025-06-15 - [Critical] Mixed-Quote Bypass in Subprocess Secret Redaction
**Vulnerability:** The application attempted to redact credential helper strings using three separate regular expressions targeting double quotes, single quotes, and unquoted strings independently. This approach was vulnerable to mixed-quote bypasses (e.g., `echo password='my'"'"'secret'`) where none of the individual regexes would fully match the shell token, resulting in the password leaking in subprocess logs.
**Learning:** Shell interpreters process string concatenation via adjacent quoting (e.g., `'a'"b"`). Parsing these complex token boundaries with disjointed regexes fails to securely match the true string boundary.
**Prevention:** Use a single unified regex pattern that matches the entire shell token by combining unquoted characters, single-quoted strings, and double-quoted strings (e.g., `r'(echo password=)(?:[^;\r\n\s\'"]|\'[^\']*\'|"(?:\\.|[^"\\])*")+'`).

## 2026-06-25 - [Argument Injection in System Open Commands (Linux/macOS)]
**Vulnerability:** The application used `os.startfile(path)` for Windows, but there was an equivalent lack of mitigation for cross-platform fallback options or when developers implement open functionally via `xdg-open` / `open` natively. If these underlying commands are used in `subprocess` to open files, an attacker could supply a path starting with a hyphen (e.g., `--help` or more malicious flags), which the command would evaluate as an option rather than a path, potentially leading to arbitrary command execution.
**Learning:** System open commands (`open` on macOS, `xdg-open` on Linux) are susceptible to argument injection just like other CLI tools. However, mitigation strategies vary by OS. `open` accepts the `--` argument separator, whereas `xdg-open` does not support it reliably across all desktop environments.
**Prevention:** For macOS `open`, always use the `--` separator (`subprocess.run(["open", "--", path])`). For Linux `xdg-open`, manually sanitize paths starting with `-` by prepending `./` to force evaluation as a relative file path (`subprocess.run(["xdg-open", f"./{path}" if path.startswith("-") else path])`). Windows `os.startfile` does not parse command-line arguments in this manner and is inherently safe.
