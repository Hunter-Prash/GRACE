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

const openNativeApp = (resourceName) => {
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


const openWebsite = (url) => {
    return new Promise((resolve, reject) => {
        console.log(`Attempting to open website: ${url}`);
        // Windows 'start' can open URLs in the default browser natively
        exec(`start "" "${url}"`, (error, stdout, stderr) => {
            if (error) {
                console.error(`exec error: ${error}`);
                return reject({ success: false, error: error.message });
            }
            console.log(`Successfully opened website ${url}`);
            return resolve({ success: true, message: `Opened website: ${url}` });
        });
    });
}

export const openApplications = async (resourceName) => {
    // If the string starts with http or www, Grace correctly formatted it as a URL
    if (resourceName.startsWith("http") || resourceName.startsWith("www") || resourceName.startsWith("https")) {
        return openWebsite(resourceName);
    }
    // Otherwise, treat it as a native desktop application
    else {
        return openNativeApp(resourceName);
    }
}
