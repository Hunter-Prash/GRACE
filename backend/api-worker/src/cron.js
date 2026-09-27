import { getCalendarEvents } from './services/calendar.service.js';
import { getActiveGoals } from './services/goals.service.js';
import { logToDiscord } from './services/logger.service.js';
import { getGeminiKey } from './config.js';
import { GoogleGenAI } from '@google/genai';

// Convert to IST offset strings helper
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

const getAiClient = () => {
    const key = getGeminiKey();
    if (!key) throw new Error("GEMINI_API_KEY is not set.");
    return new GoogleGenAI({ apiKey: key });
};

async function checkUpcomingEvents(now) {
    console.log("[CRON] Checking for upcoming events...");
    const future = new Date(now.getTime() + (90 * 60 * 1000));
    
    const nowIso = toIstIso(now);
    const futureIso = toIstIso(future);

    const events = await getCalendarEvents(nowIso, futureIso);

    const upcomingEvents = events.filter(e => {
        const start = new Date(e.start);
        const diffMins = (start.getTime() - now.getTime()) / (1000 * 60);
        return diffMins > 0 && diffMins <= 60;
    });

    if (upcomingEvents.length === 0) {
        console.log("[CRON] No upcoming events in the 1 hour window.");
        return;
    }

    console.log(`[CRON] Found ${upcomingEvents.length} upcoming events!`);
    const aiClient = getAiClient();
    
    const prompt = `You are Grace, an advanced, highly capable, and witty personal AI assistant for Prashant. 
Prashant has the following meeting(s) coming up within the next hour:
${JSON.stringify(upcomingEvents, null, 2)}

Generate a very short, friendly, proactive heads-up message for Prashant. Be helpful. If you want, mention that he should probably get ready or leave soon.
Keep it under 3 sentences. Output ONLY the message you want to send him. Do not use emojis unless absolutely necessary.`;

    const response = await aiClient.models.generateContent({
        model: 'gemini-3.5-flash',
        contents: prompt,
    });

    await logToDiscord(`🔔 **Proactive Heads-Up from Grace:**\n${response.text}`, false);
}

async function runWeeklyStrategy() {
    console.log("[CRON] Running Sunday Weekly Strategy Briefing...");
    
    // Fetch all active goals
    const activeGoals = await getActiveGoals();
    
    if (!activeGoals || activeGoals.length === 0) {
        console.log("[CRON] No active goals found for weekly strategy.");
        return;
    }
    
    const aiClient = getAiClient();
    const prompt = `You are Grace, an advanced personal AI assistant for Prashant. It is Sunday evening and time for his Weekly Strategy Briefing.
Here are his currently active goals and milestones from his database:
${JSON.stringify(activeGoals, null, 2)}

Write a highly motivational, strategic weekly briefing for Prashant. 
Acknowledge any milestones that are marked 'true' (completed). 
Pick out a few 'false' milestones and suggest he focus on them this upcoming week. 
Remind him of his ultimate goal of transitioning into Big Tech. 
Keep it concise, punchy, and formatted well for Discord. Do not use emojis unless absolutely necessary.`;

    const response = await aiClient.models.generateContent({
        model: 'gemini-3.5-flash',
        contents: prompt,
    });

    await logToDiscord(`📅 **Sunday Weekly Strategy Briefing:**\n\n${response.text}`, false);
}

async function runStagnantGoalDetector() {
    console.log("[CRON] Running Stagnant Goal Detector...");
    
    const activeGoals = await getActiveGoals();
    
    if (!activeGoals || activeGoals.length === 0) {
        return;
    }
    
    const aiClient = getAiClient();
    const prompt = `You are Grace, an advanced personal AI assistant. 
Here are Prashant's currently active goals and their 'LastUpdated' timestamps:
${JSON.stringify(activeGoals, null, 2)}

Today's date is: ${new Date().toISOString()}

Analyze the goals. If any goal hasn't been updated in over 30 days, generate a gentle but firm message for Prashant calling him out on those specific stagnant goals. Ask him if he wants to pause them, delete them, or break them down.
If NO goals are stagnant (all updated within 30 days), output exactly the string: NO_STAGNANT_GOALS`;

    const response = await aiClient.models.generateContent({
        model: 'gemini-3.5-flash',
        contents: prompt,
    });

    const text = response.text.trim();
    if (text !== "NO_STAGNANT_GOALS") {
        await logToDiscord(`⚠️ **Stagnant Goal Alert:**\n\n${text}`, false);
    }
}

export const handler = async (event) => {
    try {
        console.log("[CRON] Running Grace Proactive Cron Job (Dispatcher)...");
        
        const now = new Date(); // Current time in UTC
        const istTime = new Date(now.getTime() + (5.5 * 60 * 60 * 1000)); // Get current time in IST
        
        // 1. Every 1 Hour: Check for upcoming calendar events
        await checkUpcomingEvents(now);

        // 2. Sundays at 6:00 PM IST: Run Weekly Strategy
        // getDay() 0 = Sunday, getHours() 18 = 6 PM
        if (istTime.getDay() === 0 && istTime.getHours() === 18) {
            await runWeeklyStrategy();
        }

        // 3. 1st of every month at 9:00 AM IST: Stagnant Goal Detector
        if (istTime.getDate() === 1 && istTime.getHours() === 9) {
             await runStagnantGoalDetector();
        }

        return { statusCode: 200, body: 'Successfully ran cron dispatcher.' };
    } catch (e) {
        console.error("[CRON] Error in cron handler:", e);
        return { statusCode: 500, body: e.message };
    }
};
