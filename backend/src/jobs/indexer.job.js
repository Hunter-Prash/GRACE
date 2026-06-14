import { GoogleGenAI } from '@google/genai';
import { RecursiveCharacterTextSplitter } from "@langchain/textsplitters";
import { upsertQuery, getEmbedding } from "../services/rag.service.js";
import { getISTTimestamp } from "../services/db.client.js";

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
    const todayIST = getISTTimestamp().split('T')[0];
    const summarizationPrompt = `
You are a memory archivist for Grace, a Life OS. 
Extract a bulleted list of only the concrete facts, life events, decisions, and preferences from the NEW TRANSCRIPT.
Completely ignore small talk, greetings, filler words, and routine task outputs. 
Keep it concise and highly factual.

*** DEDUPLICATION RULES ***
1. If a fact in the NEW TRANSCRIPT means the exact same thing as a fact in the [EXISTING KNOWLEDGE] block, IGNORE IT. Do not extract it.
2. If a fact in the NEW TRANSCRIPT contradicts the [EXISTING KNOWLEDGE] (e.g. user changed their mind), DO EXTRACT IT so we can record the state change.

CRITICAL INSTRUCTION: You MUST prefix every single bullet point with the exact date: [${todayIST}].
Example: 
- [${todayIST}] Prashant decided to focus on Go instead of Java.
    `;

    for (let i = 0; i < rawBatches.length; i++) {
        if (i > 0) {
            console.log("[Indexer] Sleeping for 8 seconds to respect the 15 RPM API limit...");
            await sleep(8000);
        }

        console.log(`[Indexer] Sending Batch ${i + 1} to gemini-2.5-flash-lite for summarization...`);
        try {
            console.log(`[Indexer] Searching Pinecone for existing context...`);
            const pineconeRes = await getEmbedding(rawBatches[i], 15);
            let existingKnowledgeStr = "";
            if (pineconeRes && pineconeRes.result && pineconeRes.result.hits) {
                const hits = pineconeRes.result.hits.filter(h => h.score > 0.3); // Filter out absolute junk
                if (hits.length > 0) {
                    existingKnowledgeStr = hits.map(h => `- ${h.fields.text || h.fields.chunk_text}`).join("\n");
                }
            }

            let response;
            let retries = 3;
            while (retries > 0) {
                try {
                    response = await ai.models.generateContent({
                        model: 'gemini-2.5-flash-lite',
                        contents: `${summarizationPrompt}\n\n[EXISTING KNOWLEDGE]\n${existingKnowledgeStr || "None."}\n\n[NEW TRANSCRIPT]\n${rawBatches[i]}`
                    });
                    break;
                } catch (err) {
                    const is503 = err.status === 503 || (err.message && err.message.includes('503')) || (err.message && err.message.toLowerCase().includes('high demand'));
                    if (is503 && retries > 1) {
                        retries--;
                        console.warn(`[Indexer] 503 High Demand detected. Retrying in ${4 - retries} seconds... (${retries} left)`);
                        await sleep((4 - retries) * 2000);
                    } else {
                        throw err;
                    }
                }
            }

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
