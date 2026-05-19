
## 2026-05-18 - [Credential Helper Log Leakage Prevention]
**Vulnerability:** The application executes `git` processes with an inline credential helper string (e.g. `credential.helper=!f() { echo username=token; echo password=$TOKEN; }; f`). The `sanitize_token` function only stripped passwords from URLs but left the credential helper string unmodified. If a `subprocess.CalledProcessError` occurs, this raw command is written out in logs/stacktraces.
**Learning:** Hardcoded commands with secrets in shell strings (like credential helpers) represent an often-overlooked path for secret leakage when dealing with process exceptions.
**Prevention:** Ensure `sanitize_token` explicitly scans for and redacts `echo password=...` assignments or any other similar inline secret injection patterns.
## 2026-05-19 - [Path Traversal in Arbitrary File Deletion]
**Vulnerability:** The application used an unsanitized string `folder_name` from a package configuration (`managed_folders`) and combined it with a base directory using `pathlib.Path`'s `/` operator. The resulting path was then deleted using `shutil.rmtree()`. A malicious configuration could set `managed_folders` to `../../../../../etc` and delete arbitrary system directories.
**Learning:** `pathlib.Path(base) / unsanitized_string` is vulnerable to path traversal if `unsanitized_string` contains `../` or absolute paths (e.g. `/etc`). `pathlib` resolves `../` automatically but can result in paths outside the intended base directory.
**Prevention:** Always use `.resolve().is_relative_to(base.resolve())` to guarantee that paths generated from user input remain within their expected sandbox before performing destructive operations like file deletions or copying.
