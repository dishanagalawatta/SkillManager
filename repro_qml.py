import os
import sys
from pathlib import Path

# Force QML style
os.environ["QT_QUICK_CONTROLS_STYLE"] = "Basic"
os.environ["QT_QPA_PLATFORM"] = "offscreen"

import PySide6
from PySide6.QtWidgets import QApplication
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent, qmlRegisterSingletonInstance
from PySide6.QtCore import QUrl, QObject, Property
import PySide6.QtQuick

class AppController(QObject):
    @Property(str, constant=True)
    def statusMessage(self):
        return "Ready"

def main():
    # REGISTER BEFORE QApplication? No, QObject needs an app instance usually.
    # But let's try.
    
    app = QApplication(sys.argv)
    
    controller = AppController()
    qmlRegisterSingletonInstance(AppController, "App", 1, 0, "AppController", controller)
    
    engine = QQmlApplicationEngine()

    qml_file = Path(__file__).parent / "Test.qml"
    print(f"Loading {qml_file}")
    
    component = QQmlComponent(engine, QUrl.fromLocalFile(str(qml_file)))
    if component.isError():
        for error in component.errors():
            print(f"Error: {error.toString()}")
        sys.exit(1)
    
    obj = component.create()
    if obj is None:
        print("Failed to create object")
        sys.exit(1)
        
    print("Successfully loaded and created QML object")

if __name__ == "__main__":
    main()
