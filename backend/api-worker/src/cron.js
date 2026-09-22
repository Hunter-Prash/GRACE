import { getCalendarEvents } from './services/calendar.service.js';
import { logToDiscord } from './services/logger.service.js';
import { getGeminiKey } from './config.js';
import { GoogleGenAI } from '@google/genai';

export const handler = async (event) => {
    try {
        console.log("[CRON] Running Grace Proactive Cron Job...");

        const now = new Date();

        // 1. We want to fetch events from now to +45 minutes just to be safe
        const future = new Date(now.getTime() + (45 * 60 * 1000));

        // Convert to IST offset strings
        const pad = (n) => n < 10 ? '0' + n : n;
        const toIstIso = (d) => {
            const istDateObj = new Date(d.getTime() + (5.5 * 60 * 60 * 1000));
            return istDateObj.getUTCFullYear() +
                '-' + pad(istDateObj.getUTCMonth() + 1) +
                '-' + pad(istDateObj.getUTCDate()) +
                'T' + pad(istDateObj.getUTCHours()) +
                ':' + pad(istDateObj.getUTCMinutes()) +
                ':' + pad(istDateObj.getUTCSeconds()) +
                '+05:30';
        };

        const nowIso = toIstIso(now);
        const futureIso = toIstIso(future);

        const events = await getCalendarEvents(nowIso, futureIso);

        // Filter events that start within 15 to 30 minutes from now
        // This ensures the 15-minute cron only catches an event exactly once.
        const upcomingEvents = events.filter(e => {
            const start = new Date(e.start);
            const diffMins = (start.getTime() - now.getTime()) / (1000 * 60);
            return diffMins > 15 && diffMins <= 30;
        });

        if (upcomingEvents.length === 0) {
            console.log("[CRON] No upcoming events in the 15-30m window.");
            return { statusCode: 200, body: 'No notifications needed.' };
        }

        console.log(`[CRON] Found ${upcomingEvents.length} upcoming events in the window! Invoking Grace...`);

        // 2. We have events to notify! Generate a response with Gemini.
        const key = getGeminiKey();
        if (!key) throw new Error("GEMINI_API_KEY is not set.");

        const aiClient = new GoogleGenAI({ apiKey: key });

        const prompt = `You are Grace, an advanced, highly capable, and witty personal AI assistant for Prashant. 
Prashant has the following meeting(s) coming up in about 15-30 minutes:
${JSON.stringify(upcomingEvents, null, 2)}

Generate a very short, friendly, proactive heads-up message for Prashant. Be helpful. If you want, mention that he should probably get ready or leave soon.
Keep it under 3 sentences. Output ONLY the message you want to send him. Do not use emojis unless absolutely necessary.`;

        const response = await aiClient.models.generateContent({
            model: 'gemini-3.5-flash',
            contents: prompt,
        });

        const graceMessage = response.text;
        console.log("[CRON] Generated message:", graceMessage);

        // 3. Ping Discord
        await logToDiscord(`🔔 **Proactive Heads-Up from Grace:**\n${graceMessage}`, false);

        return { statusCode: 200, body: 'Successfully sent proactive notification.' };
    } catch (e) {
        console.error("[CRON] Error in cron handler:", e);
        return { statusCode: 500, body: e.message };
    }
};
