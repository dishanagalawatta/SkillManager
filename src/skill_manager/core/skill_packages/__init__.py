from .config import (
    _detect_command_type,
    _parse_npx_command,
    _split_args,
    detect_package_config,
    normalize_skill_package_config,
)
from .process import _resolve_process_command, run_process as _run_process, sanitize_token
from .relocator import (
    _merge_and_move_lockfile,
    _relocate_path_internal,
    relocate_packages,
    relocate_packages as _relocate_packages,
)
from .storage import (
    diff_package_inventory,
    inventory_removals_verified,
    package_project_path_conflicts,
    promote_package_storage,
    resolve_package_storage,
    scan_package_inventory,
)
from .updater import (
    _intercept_cross_platform_command,
    _run_git_package_update,
    _run_npx_update,
    _run_shell_command,
    run_skill_package_update,
)
from .versioning import (
    check_skill_package_versions,
    detect_git_remote,
    get_git_tag,
    run_version_command,
)

__all__ = [
    "normalize_skill_package_config",
    "detect_package_config",
    "run_skill_package_update",
    "check_skill_package_versions",
    "get_git_tag",
    "run_version_command",
    "sanitize_token",
    "relocate_packages",
    "detect_git_remote",
    "resolve_package_storage",
    "scan_package_inventory",
    "diff_package_inventory",
    "inventory_removals_verified",
    "promote_package_storage",
    "package_project_path_conflicts",
    # Legacy / Internal exports for tests
    "_detect_command_type",
    "_parse_npx_command",
    "_split_args",
    "_intercept_cross_platform_command",
    "_run_git_package_update",
    "_run_npx_update",
    "_run_shell_command",
    "_run_process",
    "_resolve_process_command",
    "_relocate_packages",
    "_merge_and_move_lockfile",
    "_relocate_path_internal",
]
