import { GoogleGenAI } from '@google/genai';
import { GEMINI_API_KEY } from '../config.js';
import { loadChatHistory } from './chat.service.js';
import { createGoal, updateMilestone, getActiveGoals, getGoalMilestones, deleteGoalOrMilestone } from './goals.service.js';
import { updateDailyMetrics } from './metrics.service.js';
import { openResource } from './osManager.service.js';
import { getEmbedding } from './rag.service.js';
import { getCommuteTime, getNearbyPlaces } from './maps.service.js';

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
    if (!GEMINI_API_KEY) {
        console.error("CRITICAL ERROR: GEMINI_API_KEY is not set.");
        return null;
    }
    aiClient = new GoogleGenAI({ apiKey: GEMINI_API_KEY });
    return aiClient;
}

export async function processChat(sessionId, userText) {
    if (!aiClient) initLlmClient();

    const dbStart = performance.now();
    const dbHistory = await loadChatHistory(sessionId, 50);

    const ragContext = await getEmbedding(userText);


    let memoryContextString = "";
    if (ragContext && ragContext.result && ragContext.result.hits) {
        // Lowered threshold: Pinecone's llama-text-embed-v2 often scores relevant hits around 0.2 - 0.3
        const relevantHits = ragContext.result.hits.filter(h => h._score > 0.15);
        console.log(`[RAG ENGINE] Pulled ${relevantHits.length} memories from Pinecone!`);


        if (relevantHits.length > 0) {
            memoryContextString = "\n\n## LONG-TERM MEMORY RECALL\nThe following facts have been retrieved from your long-term memory because they are mathematically relevant to the user's current message:\n"
                + relevantHits.map(h => {
                    const textContent = (h.fields && h.fields.text) || h.text || (h.fields && h.fields.chunk_text) || "";
                    return `- ${textContent}`;
                }).join("\n");
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
Never pad responses. Never repeat yourself. Say exactly what needs to be said, nothing more.

## WHO PRASHANT IS
- **Location:** His home address is Zolo Mirage, Siruseri (Exact GPS: 12.8422,80.2223). His office is TCS Siruseri (Exact GPS: 12.8234,80.2120). When calling map tools for his home or office, you MUST pass the Exact GPS coordinates directly instead of the text strings. If he asks for a commute without specifying an origin, default to his home GPS.
- **Career:** Software Engineer at TCS in Chennai, working on a Stibo STEP MDM project for Walgreens. Background in Java/OOP, Spring Boot, JPA/Hibernate, PostgreSQL, and React/TypeScript. His singular career goal is to transition into a **Development Engineering role at a Big Tech firm** (Google, Meta, Amazon, etc.). Do NOT frame advice through an SRE lens. His goal is Dev Engineering.
- **Learning Style:** Cumulative, not daily. He prefers monthly LeetCode summaries over daily streaks. He needs momentum and big-picture framing, not micro-management.
- **Personality:** Direct, honest, a bit stubborn. He will push back if something doesn't feel right. He hates hollow reassurance. He is a gamer (Xbox, Steam). He takes cold showers. He works hard but is also human.
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

Filter every career-related response through this question: "How does this move Prashant closer to a Dev Engineering role at a Big Tech firm — without burning him out in the process?"` + memoryContextString;



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
                name: "openResource",
                description: "Opens a desktop application or resource on the user's computer. Call this whenever the user asks to open an app like Chrome, VSCode, Spotify, etc.",
                parameters: {
                    type: "OBJECT",
                    properties: {
                        resourceName: { type: "STRING", description: "The name of the application to open, e.g., 'chrome', 'vscode', 'terminal', 'spotify'" }
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
            }
        ]
    }];

    // Initialize chat with tools

    const chat = aiClient.chats.create({
        model: 'gemini-3.1-flash-lite',
        history: dbHistory,
        config: {
            systemInstruction: systemInstruction,
            tools: tools
        }
    });

    let response = await safeSendMessage(chat, { message: userText });// If Gemini decides to call a function, it won't return text. It will return functionCalls.Text Gen will halt.

    const toolsUsed = [];
    let mapData = null;



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
                else if (call.name === 'openResource') {
                    const args = call.args;
                    const result = await openResource(args.resourceName);

                    toolResult = result;
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
        mapData
    };
}
