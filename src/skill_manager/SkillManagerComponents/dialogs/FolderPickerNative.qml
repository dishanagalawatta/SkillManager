/**
 * Purpose: A wrapper for the native folder selection dialog with platform path normalization.
 * Usage: 
 * FolderPickerNative {
 *     id: picker
 *     onFolderSelected: (path) => console.log(path)
 * }
 * picker.open()
 */
import QtQuick
import QtQuick.Dialogs
import SkillManagerComponents 1.0

FolderDialog {
    id: root
    
    property string mode: "path" // "path", "source", "target"
    
    signal folderSelected(string path)
    
    title: {
        switch(mode) {
            case "source": return "Select Master Source Directory"
            case "target": return "Select Project Target Directory"
            default: return "Select Target Installation Path"
        }
    }
    
    onAccepted: {
        // Convert file URL to local path
        let path = selectedFolder.toString()
        if (path.startsWith("file:///")) {
            path = path.replace("file:///", "")
        }
        
        // Fix Windows path formatting if needed
        path = path.replace(/\//g, "\\")
        let localPath = decodeURIComponent(path)
        
        folderSelected(localPath)
    }
}
