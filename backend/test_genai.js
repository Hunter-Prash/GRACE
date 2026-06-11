import { GoogleGenAI } from '@google/genai';
import { GEMINI_API_KEY } from './src/config.js';

const ai = new GoogleGenAI({ apiKey: GEMINI_API_KEY });

async function run() {
    const chat = ai.chats.create({
        model: 'gemini-3.1-flash-lite',
        config: {
            tools: [{
                functionDeclarations: [
                    {
                        name: "createGoal",
                        description: "Creates a goal",
                        parameters: { type: "OBJECT", properties: { goalId: {type: "STRING"} } }
                    }
                ]
            }]
        }
    });

    console.log("Sending message...");
    let response = await chat.sendMessage({ message: "Create a goal named test-goal" });
    console.log("Function Calls:", JSON.stringify(response.functionCalls, null, 2));

    if (response.functionCalls && response.functionCalls.length > 0) {
        const call = response.functionCalls[0];
        const functionResponses = [{
            functionResponse: {
                name: call.name,
                response: { success: true }
            }
        }];
        
        console.log("Sending function response...");
        response = await chat.sendMessage({ message: functionResponses });
        console.log("Success with { message: array }:", response.text);
    }
}
run().catch(console.error);
