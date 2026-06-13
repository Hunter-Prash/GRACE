import { GoogleGenAI } from '@google/genai';
import { RecursiveCharacterTextSplitter } from "langchain/text_splitter";
import { upsertQuery } from "../services/rag.service.js";

// We instantiate a dedicated client for the background job to keep it decoupled from the core LLM service
// (Requires process.env.GEMINI_API_KEY to be set in your environment)
const ai = new GoogleGenAI({ apiKey: process.env.GEMINI_API_KEY });

const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));

export const runMemoryIndexer = async (unindexedConversations) => {
    if (!unindexedConversations || unindexedConversations.length === 0) {
        console.log("[Indexer] No new conversations to index.");
        return 0;
    }

    console.log(`[Indexer] Processing ${unindexedConversations.length} new messages for long-term memory...`);

    // 1. Reconstruct the transcript
    const fullTranscript = unindexedConversations
        .map(msg => `${msg.role === 'model' ? 'Grace' : 'User'}: ${msg.text}`)
        .join("\n\n");

    // 2. Batching Logic to protect token limits (~800k chars = 200k tokens)
    const MAX_CHARS_PER_BATCH = 500000; // Extremely safe ceiling
    const rawBatches = [];
    let currentBatch = "";
    
    // Split by messages to avoid cutting sentences in half
    const lines = fullTranscript.split("\n\n");
    for (const line of lines) {
        if (currentBatch.length + line.length > MAX_CHARS_PER_BATCH) {
            rawBatches.push(currentBatch);
            currentBatch = line;
        } else {
            currentBatch += (currentBatch ? "\n\n" : "") + line;
        }
    }
    if (currentBatch) rawBatches.push(currentBatch);

    console.log(`[Indexer] Split payload into ${rawBatches.length} batch(es) to protect the 250k token context window.`);

    // 3. Summarization with Gemini 2.5 Flash Lite
    const allSummarizedFacts = [];
    const summarizationPrompt = `
You are a memory archivist for Grace, a Life OS. 
Extract a bulleted list of only the concrete facts, life events, decisions, and preferences from this chat transcript.
Completely ignore small talk, greetings, filler words, and routine task outputs. 
Keep it concise and highly factual.

CRITICAL INSTRUCTION: You MUST prefix every single bullet point with the exact date: [${new Date().toISOString().split('T')[0]}].
Example: 
- [${new Date().toISOString().split('T')[0]}] Prashant decided to focus on Go instead of Java.
    `;

    for (let i = 0; i < rawBatches.length; i++) {
        if (i > 0) {
            console.log("[Indexer] Sleeping for 8 seconds to respect the 15 RPM API limit...");
            await sleep(8000); 
        }

        console.log(`[Indexer] Sending Batch ${i + 1} to gemini-2.5-flash-lite for summarization...`);
        try {
            const response = await ai.models.generateContent({
                model: 'gemini-2.5-flash-lite',
                contents: `${summarizationPrompt}\n\nTRANSCRIPT:\n${rawBatches[i]}`
            });

            allSummarizedFacts.push(response.text);
        } catch (err) {
            console.error(`[Indexer] Failed to summarize batch ${i + 1}:`, err.message);
        }
    }

    const finalSummaryString = allSummarizedFacts.join("\n\n");
    if (!finalSummaryString.trim()) {
         console.log("[Indexer] No meaningful facts were extracted from this session. Skipping Pinecone upsert.");
         return 0;
    }

    // 4. Chunking the CLEAN data with LangChain
    console.log("[Indexer] Feeding clean facts into LangChain Text Splitter...");
    const splitter = new RecursiveCharacterTextSplitter({
        chunkSize: 400,   
        chunkOverlap: 50, 
    });

    const documents = await splitter.createDocuments([finalSummaryString]);
    console.log(`[Indexer] LangChain chopped the facts into ${documents.length} optimal vectors.`);

    // 5. Upsert to Pinecone Integrated Embeddings
    const pineconeRecords = documents.map((doc, index) => ({
        _id: `chat-memory-${Date.now()}-${index}`,
        text: doc.pageContent,
        category: "chat_history"
    }));

    await upsertQuery(pineconeRecords);
    console.log("[Indexer] Successfully vectorized and stored pure, high-signal memories in Pinecone!");
    
    return pineconeRecords.length;
}
