import { exec } from "child_process";


// The Translation Layer: Messy human names -> Exact Windows executables
const appDictionary = {
    // Browsers
    "chrome": "chrome",
    "google chrome": "chrome",
    "edge": "msedge",
    "microsoft edge": "msedge",
    "brave": "brave",
    "brave browser": "brave",

    // Dev Tools
    "vscode": "code",
    "visual studio code": "code",
    "terminal": "wt", // Opens Windows Terminal
    "command prompt": "cmd",

    // Office & Utilities
    "word": "winword",
    "microsoft word": "winword",
    "excel": "excel",
    "powerpoint": "powerpnt",
    "calculator": "calc.exe",
    "notepad": "notepad",

    // Media & Gaming
    "spotify": "spotify:",
    "vlc": "vlc",
    "steam": "steam://",
    "epic": "com.epicgames.launcher://",
    "epic games": "com.epicgames.launcher://",
    "epic games launcher": "com.epicgames.launcher://"
};



export const openResource = (resourceName) => {
    return new Promise((resolve, reject) => {
        const executable = appDictionary[resourceName.toLowerCase().trim()];
        console.log(`Attempting to open: ${executable}`);
        if (!executable) return reject({ success: false, error: "Application not found" });

        exec(`start "" "${executable}"`, (error, stdout, stderr) => {
            if (error) {
                console.error(`exec error: ${error}`);
                return reject({ success: false, error: error.message });
            }
            console.log(`Successfully launched ${resourceName}`);
            return resolve({ success: true, message: `Opened ${resourceName}` });
        });
    });
}