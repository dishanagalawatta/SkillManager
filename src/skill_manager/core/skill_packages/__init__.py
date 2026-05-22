from .config import (
    normalize_skill_package_config,
    detect_package_config,
    _detect_command_type,
    _parse_npx_command,
    _split_args,
)
from .updater import (
    run_skill_package_update,
    _intercept_cross_platform_command,
    _run_git_package_update,
    _run_npm_update,
    _run_shell_command,
)
from .versioning import check_skill_package_versions, get_git_tag, run_version_command, detect_git_remote
from .process import sanitize_token, run_process as _run_process, _resolve_process_command
from .relocator import (
    relocate_packages_from_output,
    relocate_packages_from_output as _relocate_packages_from_output,
    _merge_and_move_lockfile,
    _relocate_path_internal,
)

__all__ = [
    "normalize_skill_package_config",
    "detect_package_config",
    "run_skill_package_update",
    "check_skill_package_versions",
    "get_git_tag",
    "run_version_command",
    "sanitize_token",
    "relocate_packages_from_output",
    "detect_git_remote",
    # Legacy / Internal exports for tests
    "_detect_command_type",
    "_parse_npx_command",
    "_split_args",
    "_intercept_cross_platform_command",
    "_run_git_package_update",
    "_run_npm_update",
    "_run_shell_command",
    "_run_process",
    "_resolve_process_command",
    "_relocate_packages_from_output",
    "_merge_and_move_lockfile",
    "_relocate_path_internal",
]
