# System Design
> Generated via /design-md & /brainstorming

## Architectural Patterns
- **Controllers**: Singleton patterns mediating between PySide6 and standard Python (e.g. `OpsController`, `AppController`).
- **QML UI**: Token-based `Theme.qml` mapped strictly to semantic UI tokens.
- **Multiprocessing**: Replaced ThreadPoolExecutor with `joblib.Parallel` to keep the PySide6 event loop responsive during heavy parsing.
