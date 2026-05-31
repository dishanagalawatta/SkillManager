import os
import re
import shutil
import subprocess
import time
from collections.abc import Callable


def sanitize_token(text: str) -> str:
    """Removes sensitive authentication tokens from URLs and credential helpers."""
    if not isinstance(text, str):
        return text
    # Matches http://token@ or https://token@ and masks the token part
    if "@" in text and ("http://" in text or "https://" in text):
        text = re.sub(r"(https?://)[^@/\s]+@", r"\1***@", text)
    # Matches echo password=... in git credential helpers
    if "echo password=" in text:
        # Robustly redact multiline passwords within Git credential helpers.
        text = re.sub(r"(echo password=).*?(?=; \}; f)", r"\1***", text, flags=re.DOTALL)
        # Fail-safe fallback: redact the rest of the line for any unclosed or plain password logs.
        text = re.sub(r"(echo password=).*", r"\1***", text)
    return text

def _emit(output_callback: None | Callable[[str], None], message: str):
    message = sanitize_token(str(message))
    # Print to terminal for debugging and visibility
    if (
        message.startswith("[DEBUG]")
        or message.startswith("[ERROR]")
        or "Relocating" in message
        or "Success" in message
    ):
        print(message)
    if output_callback:
        output_callback(message)

def _resolve_process_command(command: str | list[str], shell: bool = False) -> str | list[str]:
    if shell or not isinstance(command, list) or not command:
        return command

    executable = command[0]
    if os.path.isabs(executable) or os.sep in executable or (os.altsep and os.altsep in executable):
        return command

    resolved = shutil.which(executable)
    if not resolved:
        raise FileNotFoundError(
            f"Executable '{executable}' was not found on PATH while running: {' '.join(command)}"
        )
    return [resolved, *command[1:]]

def run_process(
    command: str | list[str],
    output_callback: Callable[[str], None] = None,
    shell: bool = False,
    cwd: str | os.PathLike | None = None,
):
    command = _resolve_process_command(command, shell)
    process = subprocess.Popen(
        command,
        shell=shell,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
    )
    last_emit_time = 0

    if process.stdout is not None:
        for line in process.stdout:
            line_clean = sanitize_token(line.strip())
            if line_clean:
                # Always print to terminal for visibility
                print(f"[PROCESS] {line_clean}")

                # Throttle progress-like lines to UI (e.g. "Updating files: 45%")
                is_progress = bool(re.search(r"\d+%", line_clean))
                current_time = time.time()

                if not is_progress or (current_time - last_emit_time > 0.5):
                    _emit(output_callback, line_clean)
                    if is_progress:
                        last_emit_time = current_time

    process.wait()
    if process.returncode != 0:
        sanitized_command = (
            [sanitize_token(str(arg)) for arg in command]
            if isinstance(command, list)
            else sanitize_token(str(command))
        )
        raise subprocess.CalledProcessError(process.returncode, sanitized_command)
