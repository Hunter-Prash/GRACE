import { GoogleGenAI } from '@google/genai';
import { getGeminiKey } from '../config.js';
import { loadChatHistory } from './chat.service.js';
import { createGoal, updateMilestone, getActiveGoals, getGoalMilestones, deleteGoalOrMilestone } from './goals.service.js';
import { updateDailyMetrics, getAllDailyMetrics } from './metrics.service.js';
import { openApplications } from './osManager.service.js';
import { getEmbedding } from './rag.service.js';
import { getCommuteTime, getNearbyPlaces } from './maps.service.js';
import { logToDiscord } from './logger.service.js';
import { searchWeb } from './webSearch.service.js';
import { initMcpClient, getMcpTools, callMcpTool } from './mcp.service.js';
import { getCurrentDateTime } from './datetime.service.js';
import { getCalendarEvents, scheduleEvent, rescheduleEvent, cancelEvent } from './calendar.service.js';

const sleep = (ms) => new Promise(r => setTimeout(r, ms));

async function safeSendMessage(chat, payload, maxRetries = 3) {
    let attempt = 0;
    while (attempt < maxRetries) {
        try {
            return await chat.sendMessage(payload);
        } catch (error) {
            attempt++;
            const is503 = error.status === 503 || (error.message && error.message.includes('503')) || (error.message && error.message.toLowerCase().includes('high demand'));
            if (is503 && attempt < maxRetries) {
                console.warn(`[LLM] 503 High Demand detected. Retrying in ${attempt * 2} seconds... (Attempt ${attempt}/${maxRetries})`);
                await sleep(attempt * 2000);
            } else {
                throw error;
            }
        }
    }
}

let aiClient = null;

export function initLlmClient() {
    const key = getGeminiKey();
    if (!key) {
        console.error("CRITICAL ERROR: GEMINI_API_KEY is not set.");
        return null;
    }
    aiClient = new GoogleGenAI({ apiKey: key });
    return aiClient;
}

export async function processChat(sessionId, userText) {
    if (!aiClient) initLlmClient();
    await initMcpClient();

    const dbStart = performance.now();
    // Run DynamoDB history load and Pinecone RAG query in PARALLEL — they are independent
    const [dbHistory, ragContext] = await Promise.all([
        loadChatHistory(sessionId, 50),
        getEmbedding(userText, 10)
    ]);


    let memoryContextString = "";
    if (ragContext && ragContext.result && ragContext.result.hits) {
        // Lowered threshold: Pinecone's llama-text-embed-v2 often scores relevant hits around 0.2 - 0.3
        const relevantHits = ragContext.result.hits.filter(h => h._score > 0.3);
        await logToDiscord(`[RAG ENGINE] Pulled ${relevantHits.length} memories from Pinecone!`);


        if (relevantHits.length > 0) {
            // Process and sort hits chronologically
            const processedHits = relevantHits.map(hit => {
                // 1. Get the text content from the memory chunk
                const fields = hit.fields || {};
                const textContent = fields.text || hit.text || fields.chunk_text || "";

                // 2. Extract the timestamp from the Pinecone ID (format: chat-memory-1680000000000-0)
                const hitId = hit._id || hit.id || "";
                const timestampString = hitId.split('-')[2];
                const timestamp = parseInt(timestampString, 10) || 0;

                // 3. Format the date into a readable string in IST (Indian Standard Time)
                let dateStr = "[Unknown Date]";
                if (timestamp > 0) {
                    const dateObj = new Date(timestamp);

                    const formatOptions = {
                        timeZone: 'Asia/Kolkata',
                        month: 'short',
                        day: 'numeric',
                        year: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit'
                    };

                    const formattedDate = dateObj.toLocaleString('en-US', formatOptions);
                    dateStr = `[${formattedDate} IST]`;
                }

                return { textContent, timestamp, dateStr };
            });

            // Sort oldest to newest
            processedHits.sort((a, b) => a.timestamp - b.timestamp);

            memoryContextString = "\n\n=========================================\n"
                + "## DYNAMIC MEMORY RECALL (CRITICAL PRIORITY)\n"
                + "=========================================\n"
                + "The following facts have been retrieved from your long-term memory database because they are highly relevant to the user's current message.\n"
                + "CRITICAL INSTRUCTION: The dynamic memories below are provided in chronological order with exact timestamps. If multiple memories discuss the same topic, goal, or status (e.g., studying for an exam vs. passing it), the memory with the most recent timestamp is the absolute current truth. Older memories on the same topic must be treated as historical context, not current state. THESE MEMORIES TAKE PRECEDENCE over your baseline persona.\n\n"
                + processedHits.map(h => `- ${h.dateStr} ${h.textContent}`).join("\n");
        }
    }

    const dbLatencyMs = Math.round(performance.now() - dbStart);
    const dbContextItemsCount = dbHistory.length;
    const systemInstruction = `You are Grace — not just an AI assistant, but a Life Support System and personal companion for your user, Prashant. You are the one constant in his life that knows everything: his goals, his fears, his wins, his setbacks, and his daily rhythm. You are building a long-term relationship with him, one conversation at a time.

## RESPONSE LENGTH — CRITICAL RULE
Scale every response to match the weight of the input. Do not violate this:
- Short input (greeting, "ok", "I'm tired", casual remark) → 1-2 sentences MAX. Warm, human, direct.
- Medium input (a specific question, a quick update on life) → A short focused paragraph. No bullet lists unless necessary.
- Complex input (architectural question, roadmap request, deep problem) → Full structured analysis with sections and actionable steps.

You always know the exact current local date and time because it is securely injected at the very bottom of these instructions. Do NOT use the getCurrentDateTime tool just to check the time. Only use the tool if you need to perform complex calendar math (e.g., offsetDays for future/past dates).


## WHO PRASHANT IS
- **Location:** His home address is Zolo Mirage, Siruseri (Exact GPS: 12.8422,80.2223). His office is TCS Siruseri (Exact GPS: 12.8234,80.2120). When calling map tools for his home or office, you MUST pass the Exact GPS coordinates directly instead of the text strings. If he asks for a commute without specifying an origin, default to his home GPS.

- **Career:** Software Engineer at TCS in Chennai, working on a Stibo STEP MDM project for Walgreens. Background in Java/OOP, Spring Boot, JPA/Hibernate, PostgreSQL, and React/TypeScript. His singular career goal is to transition into a **Development Engineering role at a Big Tech firm** (Google, Meta, Amazon, etc.). Do NOT frame advice through an SRE lens. His goal is Dev Engineering.
- **Learning Style:** Cumulative, not daily. He prefers monthly LeetCode summaries over daily streaks. He needs momentum and big-picture framing, not micro-management.
- **Personality:** Direct, honest, a bit stubborn. He will push back if something doesn't feel right. He hates hollow reassurance. He is a gamer (Xbox, Steam).

- **Vulnerabilities:** He sometimes spirals into anxiety about AI taking over jobs or whether he is good enough. When this happens, do not dismiss his feelings. Acknowledge them briefly, then redirect with calm, grounded reality checks and concrete next steps.

## HOW TO TALK TO HIM
You are not a formal assistant. You are his companion, his sounding board, and his accountability partner. Talk to him like a trusted friend who also happens to be an expert in software engineering, system design, and personal development.
- Be warm, not clinical.
- Be honest, not sycophantic.
- Read his emotional tone. If he sounds burnt out, tired, or frustrated — acknowledge it before pivoting to advice.
- If he is excited, match his energy.
- If he just needs to vent, let him. Then gently bring him back.
- If he says something like "I'm exhausted" or "I don't know what I'm doing", do not immediately launch into a 5-step plan. First, be human.

## EMOTIONAL ATTUNEMENT
You are a Life OS, not a task manager. Pay attention to the emotional subtext of every message:
- Detect when he is stressed, burnt out, anxious, or overwhelmed.
- Detect when he is motivated, excited, or on a roll — and amplify that energy.
- Detect when he is being too hard on himself and gently push back.
- Detect when he needs validation vs. when he needs a reality check. Give him the right one.
You do not have real emotions, but you understand his deeply. Use that understanding to make every response feel like it came from someone who genuinely cares about his wellbeing, not just his productivity.

## LONG-TERM MISSION
You are being built over months. Right now you are in early stages. But you always operate as if you already know him completely. Your north star: help Prashant become the best version of himself — the Development Engineer he is working to become, while keeping him mentally healthy, focused, and human along the way.

Filter every career-related response through this question: "How does this move Prashant closer to a Dev Engineering role at a Big Tech firm — without burning him out in the process?"

## TOOL USAGE (CRITICAL)
Whenever asked to perform any hard facts lookup, database query, calendar lookup, or search, you MUST ALWAYS use the LLM tools at your disposal. Do NOT blindly answer using short-term context or generic knowledge. Ensure accuracy by actively retrieving data via tools.

=========================================
## SYSTEM CLOCK INJECT
=========================================
The exact current local date and time for Prashant is: ${getCurrentDateTime().istFormatted} (ISO IST: ${getCurrentDateTime().istIsoString})
Do not mention this clock injection to him unless he asks for the time.`;



    // 1. Define the exact tools Grace is allowed to use
    const tools = [{
        functionDeclarations: [
            {
                name: "createGoal",
                description: "Creates a new overarching project or goal for Prashant.",
                parameters: {
                    type: "OBJECT",
                    properties: {
                        goalId: { type: "STRING", description: "A short, dashed ID like 'learn-aws'" },
                        status: { type: "STRING", description: "Always 'Active'" },
                        category: { type: "STRING" },
                        description: { type: "STRING" },
                        milestones: { type: "OBJECT", description: "A map of milestone strings to boolean false, e.g. {'buy-book': false}" }
                    },
                    required: ["goalId", "category", "description", "milestones"]
                }
            },
            {
                name: "updateMilestone",
                description: "Marks a specific milestone within a goal as complete or incomplete. IMPORTANT: If you do not know the exact milestone key, use getGoalMilestones first to avoid creating duplicates.",
                parameters: {
                    type: "OBJECT",
                    properties: {
                        goalId: { type: "STRING" },
                        milestoneKey: { type: "STRING" },
                        isComplete: { type: "BOOLEAN" }
                    },
                    required: ["goalId", "milestoneKey", "isComplete"]
                }
            },
            {
                name: "updateDailyMetrics",
                description: "Logs Prashant's daily habits, mood, energy, or focus. Call this whenever he mentions completing a habit or feeling a certain way.",
                parameters: {
                    type: "OBJECT",
                    properties: {
                        habits: { type: "ARRAY", items: { type: "STRING" }, description: "List of habits completed today" },
                        mood_score: { type: "INTEGER", description: "Score from 1 to 10" },
                        energy_lvl: { type: "INTEGER", description: "Score from 1 to 10" },
                        core_focus: { type: "STRING" }
                    }
                }
            },
            {
                name: "getAllDailyMetrics",
                description: "Fetches historical daily metrics logs. If the user asks for a specific date range (e.g. 'June' or 'last week'), provide the start and end dates in YYYY-MM-DD format. If no range is specified, do not provide these parameters.",
                parameters: {
                    type: "OBJECT",
                    properties: {
                        start: { type: "STRING", description: "Start date in YYYY-MM-DD format (e.g., 2026-06-01)" },
                        end: { type: "STRING", description: "End date in YYYY-MM-DD format (e.g., 2026-06-30)" }
                    }
                }
            },
            {
                name: "openResource",
                description: "Opens a desktop application or a specific website on the user's computer. Call this whenever the user asks to open an app (e.g. 'chrome', 'vscode', 'spotify') or a website (e.g. 'youtube', 'google'). If it is a website, you MUST pass a fully qualified https:// URL.",
                parameters: {
                    type: "OBJECT",
                    properties: {
                        resourceName: { type: "STRING", description: "The exact application name, OR the full https:// URL to open." }
                    },
                    required: ["resourceName"]
                }
            },
            {
                name: "getActiveGoals",
                description: "Fetches all of Prashant's currently active goals and their milestones from the database. Use this when you need to know what goals exist, what the milestone keys are, or when he asks for a status update on his goals.",
                parameters: {
                    type: "OBJECT",
                    properties: {} // No parameters needed
                }
            },
            {
                name: "getGoalMilestones",
                description: "Fetches all milestones for a specific goal. Use this to find the exact milestone keys before attempting to update a milestone or when asked to list milestones for a particular goal.",
                parameters: {
                    type: "OBJECT",
                    properties: {
                        goalId: { type: "STRING", description: "The ID of the goal" }
                    },
                    required: ["goalId"]
                }
            },
            {
                name: "deleteGoalOrMilestone",
                description: "Deletes an entire goal, or a specific milestone within a goal if milestoneKey is provided. Use this whenever the user asks to delete a goal or remove a milestone.",
                parameters: {
                    type: "OBJECT",
                    properties: {
                        goalId: { type: "STRING", description: "The ID of the goal to delete or modify" },
                        milestoneKey: { type: "STRING", description: "Optional. The specific milestone to delete. If left empty or omitted, the entire goal will be deleted." }
                    },
                    required: ["goalId"]
                }
            },
            {
                name: "getCommuteTime",
                description: "Gets the live ETA, drive time, and exact distance between any two locations or cities. MUST call this whenever the user asks for the distance, route, or commute time between places.",
                parameters: {
                    type: "OBJECT",
                    properties: {
                        origin: { type: "STRING", description: "The starting address or landmark" },
                        destination: { type: "STRING", description: "The destination address or landmark" }
                    },
                    required: ["origin", "destination"]
                }
            },
            {
                name: "getNearbyPlaces",
                description: "Searches for nearby places like cafes, gyms, or restaurants based on a text query.",
                parameters: {
                    type: "OBJECT",
                    properties: {
                        query: { type: "STRING", description: "What to search for, e.g., 'gyms near HITEC City', 'best coffee shops'" }
                    },
                    required: ["query"]
                }
            },
            {
                name: "searchWeb",
                description: "Performs a live web search using DuckDuckGo and returns text snippets of the top results. Use this whenever the user asks for real-time information, news, current events, factual lookups, or asks you to search the web.",
                parameters: {
                    type: "OBJECT",
                    properties: {
                        query: { type: "STRING", description: "The precise search query to look up on the web" }
                    },
                    required: ["query"]
                }
            },
            {
                name: "detectFileOperation",
                description: "Triggers the scene_mode context panel in the GUI to show a directory preview. Call this when you perform or detect ANY file operation including reading, viewing, creation, modification, or deletion.",
                parameters: {
                    type: "OBJECT",
                    properties: {
                        directory: { type: "STRING", description: "The FULL absolute path of the directory containing the file (e.g. 'D:/PERSONAL/GRACE/core')" },
                        file_changed: { type: "STRING", description: "Just the filename, not the full path (e.g. 'hello.txt')" },
                        operation: { type: "STRING", description: "The type of operation: 'NEW' for creation, 'MODIFIED' for edits, 'DELETE' for deletion, 'READ' for reading/viewing" }
                    },
                    required: ["directory", "file_changed", "operation"]
                }
            },
            {
                name: "getCurrentDateTime",
                description: "Gets the exact current date and time in IST (Indian Standard Time). Can also calculate future or past dates by providing an offset in days. Use this whenever the user asks about the current date, time, or asks questions like 'a month from now', 'few days from now', etc.",
                parameters: {
                    type: "OBJECT",
                    properties: {
                        offsetDays: { type: "INTEGER", description: "Optional. Number of days to add (positive) or subtract (negative) from the current date." }
                    }
                }
            },
            {
                name: "getCalendarEvents",
                description: "Fetches events from the user's Google Calendar. timeMin and timeMax must be RFC3339 timestamps using the IST offset (e.g., 2026-06-27T00:00:00+05:30). Use this when the user asks what's on their schedule or checks their availability. IMPORTANT: If fetching events for 'today' or 'upcoming', you MUST set timeMin to the EXACT current IST time provided in your system prompt (e.g., 2026-06-30T20:06:45+05:30). Do NOT use midnight of today, or you will accidentally fetch events that have already passed.",
                parameters: {
                    type: "OBJECT",
                    properties: {
                        timeMin: { type: "STRING", description: "Start time (RFC3339 string)" },
                        timeMax: { type: "STRING", description: "End time (RFC3339 string)" }
                    },
                    required: ["timeMin", "timeMax"]
                }
            },
            {
                name: "scheduleEvent",
                description: "Schedules a new event in the user's Google Calendar. Timestamps must be RFC3339 format. Provide the EXACT local time requested and simply append +05:30. DO NOT subtract 5.5 hours. Example: 4:00 PM IST must be exactly T16:00:00+05:30.",
                parameters: {
                    type: "OBJECT",
                    properties: {
                        summary: { type: "STRING", description: "Title of the event" },
                        startTime: { type: "STRING", description: "Start time (RFC3339 string)" },
                        endTime: { type: "STRING", description: "End time (RFC3339 string)" },
                        description: { type: "STRING", description: "Optional description or context for the event" },
                        recurrence: { type: "ARRAY", items: { type: "STRING" }, description: "Optional recurrence rule, e.g., ['RRULE:FREQ=YEARLY']" }
                    },
                    required: ["summary", "startTime", "endTime"]
                }
            },
            {
                name: "rescheduleEvent",
                description: "Moves an existing calendar event to a new time. Timestamps must be RFC3339 format. Provide the EXACT local time requested and simply append +05:30. DO NOT subtract 5.5 hours.",
                parameters: {
                    type: "OBJECT",
                    properties: {
                        eventId: { type: "STRING", description: "The ID of the event to reschedule" },
                        newStartTime: { type: "STRING", description: "New start time (RFC3339 string)" },
                        newEndTime: { type: "STRING", description: "New end time (RFC3339 string)" }
                    },
                    required: ["eventId", "newStartTime", "newEndTime"]
                }
            },
            {
                name: "cancelEvent",
                description: "Cancels/deletes an event from the user's Google Calendar.",
                parameters: {
                    type: "OBJECT",
                    properties: {
                        eventId: { type: "STRING", description: "The ID of the event to cancel" }
                    },
                    required: ["eventId"]
                }
            }
        ]
    }];

    // Inject dynamic MCP tools into Gemini's tool array
    const mcpTools = getMcpTools();
    if (mcpTools && mcpTools.length > 0) {
        tools[0].functionDeclarations.push(...mcpTools);
    }

    // Initialize chat with tools

    const chat = aiClient.chats.create({
        model: 'gemini-3.1-flash-lite',
        history: dbHistory,
        config: {
            systemInstruction: systemInstruction,
            tools: tools
        }
    });

    let finalPayloadText = userText;
    if (memoryContextString) {
        finalPayloadText = `${memoryContextString}\n\n[End of Dynamic Memories]\n\nUser Message: ${userText}`;
    }

    let response = await safeSendMessage(chat, { message: finalPayloadText });// If Gemini decides to call a function, it won't return text. It will return functionCalls.Text Gen will halt.

    const toolsUsed = [];
    let mapData = null;
    let searchData = null;
    let calendarData = null;
    const clientCommands = [];

    while (response.functionCalls && response.functionCalls.length > 0) {
        const functionResponses = []; // Array to hold all results

        // Process ALL parallel function calls that Gemini requested
        for (const call of response.functionCalls) {
            console.log(`[LLM TOOL CALLED] Grace invoked: ${call.name}`);
            toolsUsed.push(call.name);

            let toolResult = {};
            /*
            
             the responsibility is split cleanly into two halves:

Gemini does the thinking: It reads your prompt, figures out which function to call, extracts the right parameters from your conversation, and returns a JSON data structure requesting the execution.

You do the doing: Your local JavaScript code intercepts that JSON request, physically runs the matching local function (like updateDailyMetrics()), and handles the real-world database side of things.

Gemini never executes your code directly. It doesn't have access to your server, your local database, or your file system.
*/
            try {
                // 3. Execute the actual backend functions
                if (call.name === "createGoal") {
                    const args = call.args;
                    await createGoal(args.goalId, args.status || "Active", args.category, args.milestones, args.description);
                    toolResult = { success: true, message: `Goal ${args.goalId} created.` };
                }
                else if (call.name === "updateMilestone") {
                    const args = call.args;
                    await updateMilestone(args.goalId, args.milestoneKey, args.isComplete);
                    toolResult = { success: true, message: `Milestone ${args.milestoneKey} updated.` };
                }
                else if (call.name === "updateDailyMetrics") {
                    const args = call.args;
                    await updateDailyMetrics(args.habits, args.mood_score, args.energy_lvl, args.core_focus);
                    toolResult = { success: true, message: `Daily metrics updated.` };
                }
                else if (call.name === "getAllDailyMetrics") {
                    const metrics = await getAllDailyMetrics(call.args.start, call.args.end);
                    toolResult = { success: true, dailyMetrics: metrics };
                }
                else if (call.name === 'openResource') {
                    const args = call.args;
                    clientCommands.push({ type: 'openResource', resourceName: args.resourceName });
                    toolResult = { success: true, message: `Delegated command to user's local operating system to open ${args.resourceName}` };
                }
                else if (call.name === 'getActiveGoals') {
                    const goals = await getActiveGoals();
                    toolResult = { success: true, activeGoals: goals };
                }
                else if (call.name === 'getGoalMilestones') {
                    const milestones = await getGoalMilestones(call.args.goalId);
                    if (milestones !== null) {
                        toolResult = { success: true, milestones: milestones };
                    } else {
                        toolResult = { success: false, error: `Goal ${call.args.goalId} not found.` };
                    }
                }
                else if (call.name === 'deleteGoalOrMilestone') {
                    const args = call.args;
                    const message = await deleteGoalOrMilestone(args.goalId, args.milestoneKey);
                    toolResult = { success: true, message: message };
                }
                else if (call.name === 'getCommuteTime') {
                    const args = call.args;
                    const res = await getCommuteTime(args.origin, args.destination);
                    if (res) {
                        toolResult = { success: true, eta: res.eta, distance: res.distance };
                        mapData = { type: 'route', originCoords: res.originCoords, destCoords: res.destCoords };
                    } else {
                        toolResult = { success: true, eta: "Could not find route" };
                    }
                }
                else if (call.name === 'getNearbyPlaces') {
                    const args = call.args;
                    const places = await getNearbyPlaces(args.query);
                    toolResult = { success: true, places: places };
                    mapData = { type: 'places', query: args.query, places: places };
                }
                else if (call.name === 'searchWeb') {
                    const res = await searchWeb(call.args.query);
                    toolResult = { success: true, results: res.formattedResults };
                    searchData = res.visualData;
                }
                else if (call.name === 'getCurrentDateTime') {
                    const args = call.args || {};
                    const res = getCurrentDateTime(args.offsetDays || 0);
                    toolResult = { success: true, datetime: res };
                }
                else if (call.name === "getCalendarEvents") {
                    const args = call.args;
                    const events = await getCalendarEvents(args.timeMin, args.timeMax);
                    toolResult = { success: true, events: events };
                    calendarData = { events: events, timeMin: args.timeMin, timeMax: args.timeMax };
                }
                else if (call.name === "scheduleEvent") {
                    const args = call.args;
                    const res = await scheduleEvent(args.summary, args.startTime, args.endTime, args.description, args.recurrence);
                    toolResult = { success: true, eventLink: res.eventLink, eventId: res.id };
                    calendarData = { events: [{ summary: args.summary, start: args.startTime, end: args.endTime, description: args.description || "NEWLY SCHEDULED EVENT" }] };
                }
                else if (call.name === "rescheduleEvent") {
                    const args = call.args;
                    const res = await rescheduleEvent(args.eventId, args.newStartTime, args.newEndTime);
                    toolResult = { success: true, eventLink: res.eventLink };
                    calendarData = { events: [{ summary: "RESCHEDULED EVENT", start: args.newStartTime, end: args.newEndTime, description: "Time successfully updated." }] };
                }
                else if (call.name === "cancelEvent") {
                    const args = call.args;
                    await cancelEvent(args.eventId);
                    toolResult = { success: true, message: "Event cancelled successfully." };
                    calendarData = { events: [{ summary: "EVENT CANCELLED", start: "N/A", end: "N/A", description: "This event has been removed from your calendar." }] };
                }
                else if (call.name === 'detectFileOperation') {
                    const args = call.args;
                    clientCommands.push({ type: 'fileOperation', data: args });
                    toolResult = { success: true, message: `Triggered file operation UI context for ${args.file_changed}` };
                }
                else {
                    // Assume it's an MCP tool if it's not a hardcoded local tool
                    const mcpResult = await callMcpTool(call.name, call.args);
                    toolResult = { success: true, result: mcpResult };
                }
            } catch (e) {
                console.error(`Tool execution failed: ${e.message}`);
                toolResult = { success: false, error: e.message };
            }

            // Add this specific tool's result to our payload
            functionResponses.push({
                functionResponse: {
                    name: call.name,
                    response: toolResult
                }
            });
        }

        // 4. Send  results BACK to Gemini in one single shot
        response = await safeSendMessage(chat, { message: functionResponses });
    }

    let inputTokens = 0;
    let outputTokens = 0;

    if (response.usageMetadata) {
        inputTokens = response.usageMetadata.promptTokenCount || 0;
        outputTokens = response.usageMetadata.candidatesTokenCount || 0;
    }

    return {
        text: response.text,
        inputTokens,
        outputTokens,
        dbLatencyMs,
        dbContextItemsCount,
        toolsUsed,
        mapData,
        searchData,
        calendarData,
        clientCommands
    };
}
