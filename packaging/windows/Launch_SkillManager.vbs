Set WshShell = CreateObject("WScript.Shell")
' Run uv run skill-manager with window style 0 (Hidden)
' This guarantees absolutely zero console flashes from Windows.
WshShell.Run "uv run skill-manager", 0
Set WshShell = Nothing
