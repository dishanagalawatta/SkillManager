import logging
import os
import re
import shutil
import subprocess
import time
from collections import deque
from collections.abc import Callable

logger = logging.getLogger(__name__)


def sanitize_token(text: str) -> str:
    """Removes sensitive authentication tokens from URLs and credential helpers."""
    if not isinstance(text, str):
        return text
    # Matches http://token@ or https://token@ and masks the token part
    if "@" in text and ("http://" in text or "https://" in text):
        text = re.sub(r"(https?://)[^@/\s]+@", r"\1***@", text)
    # Matches echo password=... in git credential helpers
    if "echo password=" in text:
        text = re.sub(r'(echo password=)"((?:\\.|[^"\\])*)"', r'\1"***"', text)
        text = re.sub(r"(echo password=)'((?:\\.|[^'\\])*)'", r"\1'***'", text)
        text = re.sub(r'(echo password=)(?![\'"])([^;\r\n]+)', r"\1***", text)
    return text


def _emit(output_callback: None | Callable[[str], None], message: str):
    message = sanitize_token(str(message))

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
    if os.name == "nt":
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

    process = subprocess.Popen(command, **kwargs)
    last_emit_time = 0
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

                if not is_progress or (current_time - last_emit_time > 0.5):
                    _emit(output_callback, line_clean)
                    if is_progress:
                        last_emit_time = current_time

    process.wait()
    if process.returncode != 0:
        if output_log:
            logger.error("Process failed. Last output lines:")
            for logged_line in output_log:
                logger.error("[PROCESS FAILED] %s", logged_line)

        sanitized_command = (
            [sanitize_token(str(arg)) for arg in command]
            if isinstance(command, list)
            else sanitize_token(str(command))
        )
        raise subprocess.CalledProcessError(process.returncode, sanitized_command)
