import { getAuthUrl, handleAuthCallback } from './src/services/calendar.service.js';

const codeArg = process.argv[2];

if (codeArg) {
    // If the user pasted the entire redirect URL, extract the code param
    let code = codeArg.trim();
    if (code.includes('code=')) {
        try {
            const urlObj = new URL(code);
            code = urlObj.searchParams.get('code') || code;
        } catch {
            const match = code.match(/code=([^&]+)/);
            if (match) code = decodeURIComponent(match[1]);
        }
    }

    console.log("Exchanging authorization code for fresh tokens...");
    handleAuthCallback(code).then((success) => {
        if (success) {
            console.log("\n✅ SUCCESS: token.json has been refreshed and saved to backend/api-worker/token.json!");
            process.exit(0);
        } else {
            console.error("\n❌ FAILED: Could not exchange authorization code. Please verify the code and try again.");
            process.exit(1);
        }
    });
} else {
    const url = getAuthUrl();
    console.log("\n========================================================");
    console.log("GOOGLE CALENDAR RE-AUTHENTICATION HELPER");
    console.log("========================================================\n");
    console.log("1. Open this URL in your browser:\n");
    console.log(url);
    console.log("\n2. Allow access with your Google account.");
    console.log("3. The browser will redirect to a localhost URL (e.g., http://localhost/?code=4/0A...&scope=...)");
    console.log("4. Copy either the code or the entire redirected URL, and run:\n");
    console.log('   node auth_calendar.js "<CODE_OR_REDIRECT_URL>"\n');
    console.log("========================================================\n");
}

