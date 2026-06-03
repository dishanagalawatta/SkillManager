import sys
import os
import faulthandler
faulthandler.enable()
os.environ["SKILL_MANAGER_TESTING"] = "1"
os.environ["SKILL_MANAGER_SKIP_INITIAL_LOAD"] = "1"
os.environ["QT_QPA_PLATFORM"] = "offscreen"
from PySide6.QtWidgets import QApplication
app = QApplication(sys.argv)
print("Importing AppController...")
from skill_manager.app import AppController
print("Instantiating AppController...")
import threading
def print_alive():
    print("Main thread is stuck...")
    faulthandler.dump_traceback()
t = threading.Timer(3, print_alive)
t.start()
c = AppController(skip_initial_load=True)
t.cancel()
print("AppController instantiated successfully.")
c.on_quit()
print("Quit successfully.")
