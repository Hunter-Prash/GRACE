import { calendar } from '@googleapis/calendar';
import { OAuth2Client } from 'google-auth-library';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { getCurrentDateTime } from './datetime.service.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const CREDENTIALS_PATH = path.join(__dirname, '../../credentials.json');
const TOKEN_PATH = path.join(__dirname, '../../token.json');

let authClient = null;


//The app needs to tell the user:"Please login with Google."That's where the this function comes in.this does not run automatically, user has to click a button in the UI for this to run.
export function getAuthUrl() {
    if (!fs.existsSync(CREDENTIALS_PATH)) return null;
    const credentials = JSON.parse(fs.readFileSync(CREDENTIALS_PATH, 'utf8'));
    const { client_secret, client_id, redirect_uris } = credentials.installed;

    //create a temp authclient just for getting the auth url. We can't use the authClient defined above because it might already have a token. And generateAuthUrl expects an authClient without a token.
    const authClientTemp = new OAuth2Client(client_id, client_secret, redirect_uris[0]);

    return authClientTemp.generateAuthUrl({
        access_type: 'offline',
        prompt: 'consent',
        scope: ['https://www.googleapis.com/auth/calendar'],
    });
}



//after clicking allow in the redirect url page the user is redirected back to the app and the auth code is sent to this function.i have maunally wired everything up in the chat riute 

export async function handleAuthCallback(code) {
    if (!authClient && !fs.existsSync(CREDENTIALS_PATH)) return false;

    const credentials = JSON.parse(fs.readFileSync(CREDENTIALS_PATH, 'utf8'));
    const { client_secret, client_id, redirect_uris } = credentials.installed;
    const client = new OAuth2Client(client_id, client_secret, redirect_uris[0]);

    try {
        const { tokens } = await client.getToken(code);//exchange auth code for toekns
        client.setCredentials(tokens);//we attach access token and refresh token along with the credentials...
        fs.writeFileSync(TOKEN_PATH, JSON.stringify(tokens));
        authClient = client;
        console.log("[CALENDAR] Successfully authenticated and saved token.json.");
        return true;
    } catch (err) {
        console.error("[CALENDAR] Error retrieving access token", err);
        return false;
    }
}




export async function initCalendarAuth() {
    if (authClient) return authClient;

    //your app's own client_id/client_secret, downloaded from Google Cloud Console — this isn't the user's data, it's your app's identity)
    if (!fs.existsSync(CREDENTIALS_PATH)) {
        console.warn("[CALENDAR] credentials.json not found. Calendar integration disabled.");
        return null;
    }

    const credentials = JSON.parse(fs.readFileSync(CREDENTIALS_PATH, 'utf8'));
    const { client_secret, client_id, redirect_uris } = credentials.installed;

    // Use the first redirect URI from credentials
    const redirectUri = redirect_uris[0];

    //create the authClient object in memory 
    authClient = new OAuth2Client(client_id, client_secret, redirectUri);

    //Check if token.json exists (this is your personal access/refresh token from a previous login). If yes, load it into the client via setCredentials and you're done — Grace can hit Calendar right away.
    //If no token.json, return null — meaning "not authenticated yet, go run the OAuth flow."
    if (fs.existsSync(TOKEN_PATH)) {
        const token = JSON.parse(fs.readFileSync(TOKEN_PATH, 'utf8'));
        authClient.setCredentials(token);//here auth client now also has access toekn and refresh token. So this is the end of authentication. Grace can hit Calendar right away.
        console.log("[CALENDAR] Loaded existing token.json successfully.");
        return authClient;
    } else {
        console.warn("[CALENDAR] No token.json found. User must authenticate via OAuth.");
        return null;
    }
}


// ---------------------------------------------------------
// CALENDAR OPERATIONS
// ---------------------------------------------------------

export async function getCalendarEvents(timeMin, timeMax) {
    if (!authClient) await initCalendarAuth();
    if (!authClient) throw new Error("Calendar not authenticated. Please run the setup flow.");

    // Clip timeMin to the current time to strictly prevent fetching past events
    const now = new Date();
    const requestedTimeMin = new Date(timeMin);
    if (requestedTimeMin < now) {
        timeMin = getCurrentDateTime().istIsoString;
    }

    const cal = calendar({ version: 'v3', auth: authClient });

    try {
        const res = await cal.events.list({
            calendarId: 'primary',
            timeMin: timeMin,
            timeMax: timeMax,
            maxResults: 20,
            singleEvents: true,
            orderBy: 'startTime',
        });
        return res.data.items.map(event => ({
            id: event.id,
            summary: event.summary,
            description: event.description,
            start: event.start.dateTime || event.start.date,
            end: event.end.dateTime || event.end.date,
            location: event.location,
            link: event.htmlLink
        }));
    } catch (err) {
        console.error("[CALENDAR] API Error:", err.message);
        throw err;
    }
}

export async function scheduleEvent(summary, startTime, endTime, description = "", recurrence = null) {
    if (!authClient) await initCalendarAuth();
    if (!authClient) throw new Error("Calendar not authenticated.");

    const cal = calendar({ version: 'v3', auth: authClient });

    const event = {
        summary: summary,
        description: description,
        start: { dateTime: startTime, timeZone: 'Asia/Kolkata' },
        end: { dateTime: endTime, timeZone: 'Asia/Kolkata' }
    };

    if (recurrence && Array.isArray(recurrence)) {
        event.recurrence = recurrence;
    }

    try {
        const res = await cal.events.insert({
            calendarId: 'primary',
            resource: event,
        });
        return { success: true, eventLink: res.data.htmlLink, id: res.data.id };
    } catch (err) {
        console.error("[CALENDAR] Create API Error:", err.message);
        throw err;
    }
}

export async function rescheduleEvent(eventId, newStartTime, newEndTime) {
    if (!authClient) await initCalendarAuth();
    if (!authClient) throw new Error("Calendar not authenticated.");

    const cal = calendar({ version: 'v3', auth: authClient });

    try {
        // First get the existing event to keep other details
        const event = await cal.events.get({
            calendarId: 'primary',
            eventId: eventId
        });

        event.data.start = { dateTime: newStartTime, timeZone: 'Asia/Kolkata' };
        event.data.end = { dateTime: newEndTime, timeZone: 'Asia/Kolkata' };

        const res = await cal.events.update({
            calendarId: 'primary',
            eventId: eventId,
            resource: event.data,
        });
        return { success: true, eventLink: res.data.htmlLink };
    } catch (err) {
        console.error("[CALENDAR] Reschedule API Error:", err.message);
        throw err;
    }
}

export async function cancelEvent(eventId) {
    if (!authClient) await initCalendarAuth();
    if (!authClient) throw new Error("Calendar not authenticated.");

    const cal = calendar({ version: 'v3', auth: authClient });

    try {
        await cal.events.delete({
            calendarId: 'primary',
            eventId: eventId
        });
        return { success: true };
    } catch (err) {
        console.error("[CALENDAR] Cancel API Error:", err.message);
        throw err;
    }
}

// Initial setup call
initCalendarAuth();
