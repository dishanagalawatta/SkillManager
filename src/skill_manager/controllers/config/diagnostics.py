"""Cache persistence and agent-accessible diagnostic slots for the ConfigController facade."""

from PySide6.QtCore import Slot

from skill_manager.core.diagnostics import get_diagnostic_logger


class DiagnosticsMixin:
    """Skill cache persistence plus diagnostic log access slots.

    All diagnostic methods delegate to the canonical
    ``get_diagnostic_logger()`` singleton; they are agent-accessible
    via QML invokable slots.
    """

    @Slot(dict)
    def save_cache(self, data: dict):
        """Saves discovered skills to cache."""
        from skill_manager.core.persistence import save_cache

        save_cache(data)

    @Slot(result=dict)
    def load_cache(self):
        """Loads discovered skills from cache."""
        from skill_manager.core.persistence import load_cache

        return load_cache()

    @Slot(result=str)
    def getDiagnosticLogPath(self) -> str:
        """Returns the path to the diagnostic log file."""
        return get_diagnostic_logger().get_log_path()

    @Slot(int, result=str)
    def getRecentDiagnosticEvents(self, count: int = 100) -> str:
        """Returns JSON array of the most recent diagnostic events."""
        import json

        events = get_diagnostic_logger().get_recent_events(count)
        return json.dumps(events, ensure_ascii=False, default=str)

    @Slot(str, result=str)
    def exportDiagnosticBundle(self, output_dir: str = "") -> str:
        """Export diagnostic bundle (logs + manifest) as a zip file.

        Args:
            output_dir: Directory to write the zip. Defaults to log dir.

        Returns:
            Path to the created zip, or empty string on failure.
        """
        dir_path = output_dir if output_dir else None
        return get_diagnostic_logger().export_bundle(dir_path)

    @Slot()
    def clearDiagnosticLogs(self):
        """Clear all diagnostic log files and ring buffer."""
        get_diagnostic_logger().clear_logs()
        self.app._set_status("Diagnostic logs cleared")

    @Slot(result=str)
    def getDiagnosticCounts(self) -> str:
        """Returns JSON dict of diagnostic event counts by level."""
        import json

        return json.dumps(get_diagnostic_logger().get_diagnostic_counts())

    @Slot(result=str)
    def getDiagnosticHealthStatus(self) -> str:
        """Returns 'green', 'yellow', or 'red' health status."""
        return get_diagnostic_logger().get_health_status()

    @Slot(int, result=str)
    def getRecentEventsHuman(self, count: int = 20) -> str:
        """Returns JSON array of recent events in human-readable format."""
        import json

        events = get_diagnostic_logger().get_recent_events_human(count)
        return json.dumps(events, ensure_ascii=False)
