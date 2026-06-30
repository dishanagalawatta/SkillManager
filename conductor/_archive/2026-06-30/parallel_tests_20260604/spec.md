# Parallel Test Runner Specification

## Overview
Implement a script to run all tests with a single command. The script must run tests in parallel, catch failures properly, and produce noiseless output that shows progress (completed tests out of full test count) while running, and detailed errors at the end.

## Requirements
- Single command execution (`python run_tests.py` or similar).
- Parallel execution using `pytest-xdist`.
- Clean progress tracking with `pytest-sugar`.
- Detailed error reporting upon failure.