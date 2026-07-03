import shlex
import sys
command = "npx update"
print(shlex.split(command, posix=sys.platform != "win32"))
