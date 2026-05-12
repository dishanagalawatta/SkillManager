# Skill Manager

A professional desktop application for managing reusable agent skills across multiple repositories.

## Professional Features
- **Modular Architecture**: Clean separation of GUI, core logic, and utilities.
- **Cross-Repository Sync**: Effortlessly copy and update skills between source and target directories.
- **Modern UI**: Sleek, dark-themed interface built with CustomTkinter.
- **Native Integration**: Windows native window positioning support.

## Getting Started

### Prerequisites
- Python 3.10 or higher.
- `pip` for dependency management.

### Installation
Clone the repository and install dependencies:
```bash
pip install .
```

### Running the Application
Launch the Skill Manager using the module entry point:
```bash
python -m skill_manager
```

## Development
- **Source Code**: All code resides in the `src/skill_manager/` package.
- **Tests**: Run tests using `pytest`:
  ```bash
  pytest
  ```

## Building Executable
This project is configured for building with PyInstaller:
```bash
pyinstaller --name "SkillManager" --windowed src/skill_manager/__main__.py
```

## License
MIT
