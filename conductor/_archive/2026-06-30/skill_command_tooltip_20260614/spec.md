# Text Tooltip Previews for Skills and Commands

## Description
When the user hovers over a standard skill or command item in the list, a tooltip containing a text preview should appear. For skills, this will show the skill's description. For commands, this will show a snippet of the command's code.

## Architecture Constraints
- Use QML's native `ToolTip` component in `SkillItem.qml` (alongside the existing screenshot tooltip).
- Do not introduce external libraries.

## Requirements
- The tooltip must show the description if the item is a normal skill (`!model.isScreenshot && !model.isCommand && !model.isCollection`).
- The tooltip must show up to the first 10 lines of the code if the item is a command (`model.isCommand`).
- The command preview should be rendered in a monospace font.
- The tooltip should wrap text and have a maximum width of roughly 400 pixels to avoid overflowing the screen.
- Tooltip displays smoothly with a small delay (e.g. 450ms).