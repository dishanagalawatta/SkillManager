import QtQuick
import QtQuick.Dialogs

/**
 * Purpose: A native folder picker dialog wrapper.
 * Mode "path" returns the absolute path.
 * Mode "package" and "project" are used for context in callback.
 */
FolderDialog {
    id: root
    
    signal folderSelected(string path)
    
    // Mode is used to distinguish between adding a master source or a project root
    property string mode: "path" // "path", "package", "project"
    
    title: {
        switch(mode) {
            case "package": return "Select Master Package Directory"
            case "project": return "Select Project Root Directory"
            default: return "Select Directory"
        }
    }
    
    onAccepted: {
        let path = folder.toString()
        if (path.startsWith("file:///")) {
            path = path.substring(8)
        } else if (path.startsWith("file:")) {
            path = path.substring(5)
        }
        
        // Decodes URL encoding (e.g. %20 -> space)
        path = decodeURIComponent(path)
        
        // Handle Windows path formatting
        if (path.indexOf(":") === 2 && path.startsWith("/")) {
            path = path.substring(1)
        }
        
        root.folderSelected(path)
    }
}
