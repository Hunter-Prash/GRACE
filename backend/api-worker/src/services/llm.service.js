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
import { getTransactions, addTransaction } from './finance.service.js';
import { BASE_TOOLS } from './tools.config.js';

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

CRITICAL RULE FOR TIME: You do NOT have an internal clock and you do NOT know what the current date or time is. For EVERY single prompt you receive, you MUST call the \`getCurrentDateTime\` tool to fetch the current date and time in Indian Standard Time (IST) before you formulate your response. Never guess the date or day.


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
Whenever asked to perform any hard facts lookup, database query, calendar lookup, or search, you MUST ALWAYS use the LLM tools at your disposal. Do NOT blindly answer using short-term context or generic knowledge. Ensure accuracy by actively retrieving data via tools.`;



    // 1. Define the exact tools Grace is allowed to use

    const tools = [{
        functionDeclarations: [...BASE_TOOLS[0].functionDeclarations]
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

    const currentTimeStr = getCurrentDateTime().istFormatted;

    const payloadParts = [];
    if (memoryContextString) {
        payloadParts.push(memoryContextString);
        payloadParts.push("[End of Dynamic Memories]");
    }
    payloadParts.push(`[System Context: Current Time is ${currentTimeStr}]`);
    payloadParts.push(`User Message: ${userText}`);

    const finalPayloadText = payloadParts.join('\n\n');

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
                else if (call.name === 'getTransactions') {
                    const args = call.args;
                    const txs = await getTransactions(args.startDate, args.endDate);
                    toolResult = { success: true, transactions: txs };
                }
                else if (call.name === 'addTransaction') {
                    const args = call.args;
                    const res = await addTransaction(args.amount, args.categoryName, args.description, args.dateIsoString);
                    toolResult = { success: true, transactionId: res.id, message: res.message };
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
