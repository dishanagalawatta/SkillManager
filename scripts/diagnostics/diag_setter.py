import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from PySide6.QtCore import Property, QObject, Qt


class MyModel(QObject):
    def __init__(self):
        super().__init__()
        self._val = None

    @Property(Qt.CheckState)
    def val(self):
        return self._val

    @val.setter
    def val(self, value):
        print(
            "Setter received type:",
            type(value),
            "value:",
            value,
            "value.value:",
            getattr(value, "value", None),
        )

        # Test what QtModel's setter is doing:
        new_val = None
        if value == Qt.CheckState.Checked or value is True:
            new_val = True
        elif value == Qt.CheckState.Unchecked or value is False:
            new_val = False

        print("Resulting new_val:", new_val)
        self._val = new_val


model = MyModel()
print("Setting to True...")
model.val = True

print("\nSetting to False...")
model.val = False

print("\nSetting to Qt.CheckState.Checked...")
model.val = Qt.CheckState.Checked
