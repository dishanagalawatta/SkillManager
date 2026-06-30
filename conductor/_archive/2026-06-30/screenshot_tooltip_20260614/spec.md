# Screenshot Hover Preview Tooltip

## Description
When the user hovers over a screenshot item in the list, a tooltip containing a preview of the image should appear.

## Architecture Constraints
- Use QML's native `ToolTip` component.
- Customize the `contentItem` to display an `Image` based on the `model.path` property.
- Do not introduce new external libraries, as QML provides this capability out-of-the-box natively.

## Requirements
- The tooltip must only show if the item is a screenshot (`model.isScreenshot`).
- The image preview should have a reasonable maximum size (e.g., `maxWidth: 300`, `maxHeight: 300`) to not overwhelm the UI.
- The image source should be loaded with `sourceSize` scaled down to preserve memory, but `fillMode: Image.PreserveAspectFit` to maintain aspect ratio.
- The tooltip should display smoothly with a small delay (e.g. 400ms).