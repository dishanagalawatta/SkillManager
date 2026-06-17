1. Modify `src/skill_manager/core/skill_packages/process.py` to fix `sanitize_token`
   - Use the pattern described in the memory for redacting `echo password=...`.
   - The memory states:
     ```
     When using regular expressions to redact secrets embedded within shell commands or structured strings (like echo password='secret'), separate patterns for quoted and unquoted values. Avoid non-greedy matchers like (.*?) inside quotes, as they fail on escaped quotes and leak the remainder of the secret. Instead, safely handle spaces and escaped characters using escape-aware patterns, ensuring alternatives are mutually exclusive to prevent ReDoS vulnerabilities (e.g., r'(password=)"((?:\\.|[^"\\])*)"' for double quotes, and r'(password=)(?!['"])([^;\r\n]+)' for unquoted).
     ```
   - Also, `When using Python regex to redact secrets from multiline text, remember that . (dot) does not match newlines by default. To prevent 'fail open' security regressions where secrets leak if followed by a newline, explicitly include \r and \n in match boundaries or lookaheads (e.g., (?=...|\r|\n|$)) or use re.DOTALL.`
   - Also, `When using fast-path substring checks to gate regex replacements (e.g., if 'echo password=' in text:), ensure the regular expression inside the block strictly matches the condition's full context (e.g., r'(echo password=)...' instead of just r'(password=)...') to avoid unintended collateral modifications to unrelated substrings within the same text.`
   - Also, `When redacting secrets from logs or outputs using regex, avoid using greedy matches with re.DOTALL (e.g., .*) as it can cause massive data loss by consuming the entire remaining string. Instead, prefer explicit matching of known token formats...`

   The fix in `sanitize_token` will be:
   ```python
   if "echo password=" in text:
       text = re.sub(r'(echo password=)"((?:\\.|[^"\\])*)"', r'\1"***"', text)
       text = re.sub(r"(echo password=)'((?:\\.|[^'\\])*)'", r"\1'***'", text)
       text = re.sub(r'(echo password=)(?![\'"])([^;\r\n]+)', r'\1***', text)
   ```

2. Add a pytest to verify `sanitize_token` in `tests/test_process.py` (if it exists) or create one.
3. Pre commit steps to make sure proper testing, verifications, reviews and reflections are done.
4. Report my findings via PR with the required PR format (Title: "🛡️ Sentinel: [CRITICAL/HIGH] Fix [vulnerability type]").
