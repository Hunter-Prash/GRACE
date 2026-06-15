import { logToDiscord } from "./src/services/logger.service.js";

async function testLogger() {
    console.log("Testing Discord Webhook Logger...");
    
    await logToDiscord("[System] Grace backend online. Discord Logger initialized successfully.");
    await logToDiscord("[RAG ENGINE] Pulled 3 memories from Pinecone!", true); // true = bold formatted
    
    console.log("Test messages sent! Check your Discord channel.");
}

testLogger();
