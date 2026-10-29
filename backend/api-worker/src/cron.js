import { getCalendarEvents } from './services/calendar.service.js';
import { getActiveGoals, getAllGoals } from './services/goals.service.js';
import { getDueBrainDumps, getBrainDumpNotes } from './services/braindump.service.js';
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
        model: 'gemini-3.1-flash-lite',
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
        model: 'gemini-3.1-flash-lite',
        contents: prompt,
    });

    await logToDiscord(`📅 **Sunday Weekly Strategy Briefing:**\n\n${response.text}`, false);
}

async function runGoalAnalyzer() {
    console.log("[CRON] Running Weekly Goal Analyzer...");
    
    const allGoals = await getAllGoals();
    
    if (!allGoals || allGoals.length === 0) {
        console.log("[CRON] No goals found to analyze.");
        return;
    }
    
    const aiClient = getAiClient();
    const prompt = `You are Grace, an advanced personal AI assistant. 
Here are all of Prashant's goals (completed, active, in-progress, etc.):
${JSON.stringify(allGoals, null, 2)}

Today's date is: ${new Date().toISOString()}

Perform a deep, highly analytical review of everything he has accomplished so far and what is currently pending. Point out patterns, acknowledge significant completions, and highlight any potential bottlenecks in his incompleted tasks. 
Draft a comprehensive, motivating, and strategic message analyzing his overall progress. Format it well for Discord without using unnecessary emojis.`;

    const response = await aiClient.models.generateContent({
        model: 'gemini-3.1-flash-lite',
        contents: prompt,
    });

    await logToDiscord(`📊 **Saturday Goal Analysis:**\n\n${response.text}`, false);
}

async function runDailyBrainDumpReview() {
    console.log("[CRON] Running 24-Hour Daily Brain Dump Review (9:00 PM IST)...");
    const activeNotes = await getBrainDumpNotes("Active", null, 20);
    const dueNotes = await getDueBrainDumps();

    if (activeNotes.length === 0) {
        console.log("[CRON] No active Brain Dump notes found for daily review.");
        return;
    }

    console.log(`[CRON] Reviewing ${activeNotes.length} active Brain Dump notes (${dueNotes.length} due today/upcoming)...`);
    const aiClient = getAiClient();
    const prompt = `You are Grace, an advanced personal AI assistant and Life Support System for Prashant. 
It is 9:00 PM IST—time for his end-of-day Brain Dump review and mental wind-down.

Here are his current active notes, reminders, and thoughts recorded in his database:
${JSON.stringify(activeNotes.map(n => ({ content: n.Content, category: n.Category, dueDate: n.DueDate || "No deadline" })), null, 2)}

Tasks/Reminders specifically due today or upcoming:
${JSON.stringify(dueNotes.map(n => ({ content: n.Content, dueDate: n.DueDate })), null, 2)}

Write a concise, warm, and structured evening debrief for Prashant:
1. Briefly acknowledge what was noted down today / pending.
2. Flag anything urgent or due tomorrow/soon so he doesn't have it lingering in his head.
3. Keep it calming, encouraging, and under 4-5 bullet points formatted cleanly for Discord. Do not use unnecessary emojis.`;

    const response = await aiClient.models.generateContent({
        model: 'gemini-3.1-flash-lite',
        contents: prompt,
    });

    await logToDiscord(`🧠 **Daily Brain Dump & Evening Wind-Down:**\n\n${response.text}`, false);
}

async function generateDailyMotivation() {
    console.log("[CRON] Generating Daily Morning Perspective (7:00 AM IST)...");
    
    const aiClient = getAiClient();
    const prompt = `You are Grace, an insightful, grounded personal companion for Prashant. 
It is 7:00 AM in the morning.

Provide a genuinely thoughtful, powerful piece of motivational advice or philosophical perspective for him to start his day. 
Guidelines:
- Do NOT reference any goals, databases, milestones, work projects, or to-do lists.
- Keep it concise (2-3 sentences max). Formatted cleanly for Discord without unnecessary emojis.`;

    const response = await aiClient.models.generateContent({
        model: 'gemini-3.1-flash-lite',
        contents: prompt,
    });

    await logToDiscord(`🌅 **Daily Morning Perspective:**\n\n${response.text}`, false);
}

export const handler = async (event = {}) => {
    try {
        console.log("[CRON] Running Grace Proactive Cron Job (Dispatcher)...", JSON.stringify(event));
        
        const now = new Date(); // Current time in UTC
        const istTime = new Date(now.getTime() + (5.5 * 60 * 60 * 1000)); // Get current time in IST
        
        // Manual override check (for instant test triggers via EventBridge, CLI, or manual invocation)
        if (event.action === 'triggerBrainDump' || event.forceBrainDump === true) {
            console.log("[CRON] Manual Brain Dump trigger received!");
            await runDailyBrainDumpReview();
            return { statusCode: 200, body: 'Successfully executed manual Brain Dump trigger.' };
        }
        if (event.action === 'triggerMotivation' || event.forceMotivation === true) {
            console.log("[CRON] Manual Motivation trigger received!");
            await generateDailyMotivation();
            return { statusCode: 200, body: 'Successfully executed manual Motivation trigger.' };
        }
        if (event.action === 'triggerWeeklyStrategy' || event.forceStrategy === true) {
            console.log("[CRON] Manual Weekly Strategy trigger received!");
            await runWeeklyStrategy();
            return { statusCode: 200, body: 'Successfully executed manual Weekly Strategy trigger.' };
        }
        if (event.action === 'triggerGoalAnalyzer' || event.forceGoals === true) {
            console.log("[CRON] Manual Goal Analyzer trigger received!");
            await runGoalAnalyzer();
            return { statusCode: 200, body: 'Successfully executed manual Goal Analyzer trigger.' };
        }
        if (event.action === 'triggerCalendar' || event.forceCalendar === true) {
            console.log("[CRON] Manual Calendar check trigger received!");
            await checkUpcomingEvents(now);
            return { statusCode: 200, body: 'Successfully executed manual Calendar check trigger.' };
        }
        if (event.action === 'triggerAll' || event.forceAll === true) {
            console.log("[CRON] Manual Trigger ALL received!");
            await checkUpcomingEvents(now);
            await generateDailyMotivation();
            await runDailyBrainDumpReview();
            await runGoalAnalyzer();
            await runWeeklyStrategy();
            return { statusCode: 200, body: 'Successfully executed all cron triggers.' };
        }

        // 1. Every 1 Hour: Check for upcoming calendar events only
        try {
            await checkUpcomingEvents(now);
        } catch (calErr) {
            console.error("[CRON] Calendar check failed (skipping to other scheduled tasks):", calErr.message || calErr);
        }

        // 2. Once every 24 Hours at 9:00 PM IST (21:00): Daily Brain Dump Review
        if (istTime.getUTCHours() === 21) {
            try {
                await runDailyBrainDumpReview();
            } catch (err) {
                console.error("[CRON] Daily Brain Dump Review failed:", err.message || err);
            }
        }

        // 3. Sundays at 6:00 PM IST: Run Weekly Strategy
        // getDay() 0 = Sunday, getHours() 18 = 6 PM
        if (istTime.getUTCDay() === 0 && istTime.getUTCHours() === 18) {
            try {
                await runWeeklyStrategy();
            } catch (err) {
                console.error("[CRON] Weekly Strategy failed:", err.message || err);
            }
        }

        // 4. Every Saturday at 12:00 PM IST: Goal Analyzer
        if (istTime.getUTCDay() === 6 && istTime.getUTCHours() === 12) {
            try {
                await runGoalAnalyzer();
            } catch (err) {
                console.error("[CRON] Goal Analyzer failed:", err.message || err);
            }
        }

        // 5. Every day at 7:00 AM IST: Daily Motivation
        if (istTime.getUTCHours() === 7) {
            try {
                await generateDailyMotivation();
            } catch (err) {
                console.error("[CRON] Daily Motivation failed:", err.message || err);
            }
        }

        return { statusCode: 200, body: 'Successfully ran cron dispatcher.' };
    } catch (e) {
        console.error("[CRON] Error in cron handler:", e);
        return { statusCode: 500, body: e.message };
    }
};
