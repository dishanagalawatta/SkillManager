"""Run lint and full test suite in parallel.

Convenience wrapper — in CI, prefer direct uv commands:
  uv run ruff check src tests --fix
  uv run pytest -n auto --dist loadfile
"""

import subprocess
import sys


def main():
    """Execute ruff lint + pytest in sequence."""
    print("Running linter (ruff)...")
    lint_cmd = ["uv", "run", "ruff", "check", "src", "tests", "--fix"]

    try:
        lint_result = subprocess.run(lint_cmd)
        if lint_result.returncode != 0:
            print(
                f"Linting issues found (Exit code {lint_result.returncode}). Proceeding to tests..."
            )
        else:
            print("Linting clean!")

        print("\nStarting parallel test execution...")

        test_cmd = [
            "uv",
            "run",
            "pytest",
            "-n",
            "auto",  # Run tests in parallel
            "--dist",
            "loadfile",  # Distribute tests by file to avoid shared state issues
            "--tb=short",  # Use short traceback for cleaner error reporting
            "-p",
            "no:warnings",  # Suppress warnings for noiseless output
        ]

        result = subprocess.run(test_cmd)

        if result.returncode == 0:
            print("\nAll tests passed successfully!")
        else:
            print(f"\nTests failed with exit code {result.returncode}")

        sys.exit(result.returncode)

    except KeyboardInterrupt:
        print("\nTest execution interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\nAn error occurred while running tests: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
