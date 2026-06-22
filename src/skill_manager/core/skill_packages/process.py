import logging
import os
import re
import shutil
import subprocess
import time
from collections import deque
from collections.abc import Callable

logger = logging.getLogger(__name__)


def sanitize_token(text: str | None) -> str | None:
    """Removes sensitive authentication tokens from URLs and credential helpers.

    Non-string inputs (including ``None``) are returned unchanged so callers can
    preserve a ``None`` distinction between "no output yet" and "sanitized
    output".
    """
    if not isinstance(text, str):
        return text
    # Matches http://token@ or https://token@ and masks the token part
    if "@" in text and ("http://" in text or "https://" in text):
        text = re.sub(r"(https?://)[^@/\s]+@", r"\1***@", text)
    # Matches echo password=... in git credential helpers
    if "echo password=" in text:
        text = re.sub(r"(echo password=).*", r"\1***", text)
    return text


def emit(output_callback: None | Callable[[str], None], message: str):
    sanitized = sanitize_token(str(message))
    # ``sanitize_token`` only returns ``None`` for non-string inputs, and we
    # always pass a ``str`` above, so the narrowing is safe.
    assert sanitized is not None
    message = sanitized

    if message.startswith("[DEBUG]"):
        logger.debug(message)
        return

    # Print to terminal for debugging and visibility
    if message.startswith("[ERROR]"):
        logger.error(message)
    elif "Relocating" in message or "Cleaning up" in message:
        logger.debug(message)
        return  # Prevent UI spam for thousands of relocated folders
    elif "Success" in message:
        logger.info(message)

    if output_callback:
        output_callback(message)


def resolve_process_command(command: str | list[str], shell: bool = False) -> str | list[str]:
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
    output_callback: Callable[[str], None] | None = None,
    shell: bool = False,
    cwd: str | os.PathLike | None = None,
):
    command = resolve_process_command(command, shell)
    kwargs = {
        "shell": shell,
        "cwd": cwd,
        "stdout": subprocess.PIPE,
        "stderr": subprocess.STDOUT,
        "stdin": subprocess.DEVNULL,
        "text": True,
        "encoding": "utf-8",
        "errors": "replace",
        "bufsize": 1,
    }

    process = subprocess.Popen(command, **kwargs)
    lastemit_time = 0
    output_log = deque(maxlen=50)

    if process.stdout is not None:
        for line in process.stdout:
            line_clean = sanitize_token(line.strip())
            if line_clean:
                # Always print to terminal for visibility at debug level
                logger.debug("[PROCESS] %s", line_clean)
                output_log.append(line_clean)

                # Throttle progress-like lines to UI (e.g. "Updating files: 45%")
                is_progress = bool(re.search(r"\d+%", line_clean))
                current_time = time.time()

                if not is_progress or (current_time - lastemit_time > 0.5):
                    emit(output_callback, line_clean)
                    if is_progress:
                        lastemit_time = current_time

    process.wait()
    if process.returncode != 0:
        if output_log:
            logger.error("Process failed. Last output lines:")
            for logged_line in output_log:
                logger.error("[PROCESS FAILED] %s", logged_line)

        sanitized_command: list[str] | str
        if isinstance(command, list):
            sanitized_command = [
                # ``sanitize_token`` returns the input unchanged for non-str;
                # the str() cast above guarantees a str result.
                sanitize_token(str(arg)) or ""
                for arg in command
            ]
        else:
            sanitized_command = sanitize_token(str(command)) or ""
        raise subprocess.CalledProcessError(process.returncode, sanitized_command)
