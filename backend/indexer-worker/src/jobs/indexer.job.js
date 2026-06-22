import { GoogleGenAI } from '@google/genai';
import { RecursiveCharacterTextSplitter } from "@langchain/textsplitters";
import { upsertQuery, getEmbedding } from "../services/rag.service.js";
import { getISTTimestamp } from "../services/db.client.js";
import { sendIndexerNotification } from "../services/sns.service.js";
import { logToDiscord } from "../services/logger.service.js";

const ai = new GoogleGenAI({ apiKey: process.env.GEMINI_API_KEY });

const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));

export const runMemoryIndexer = async (unindexedConversations) => {
    if (!unindexedConversations || unindexedConversations.length === 0) {
        console.log("[Indexer] No new conversations to index."); // Do not send to Discord to avoid spam
        return 0;
    }

    await logToDiscord(`[Indexer] Processing ${unindexedConversations.length} new messages for long-term memory...`, true);

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

    await logToDiscord(`[Indexer] Split payload into ${rawBatches.length} batch(es) to protect the 250k token context window.`);

    // 3. Summarization with Gemini 2.5 Flash Lite
    const allSummarizedFacts = [];
    const todayIST = getISTTimestamp().split('T')[0];
    const summarizationPrompt = `
You are a memory archivist for Grace, a Life OS. 
Write a comprehensive, dense paragraph summarizing all the concrete facts, life events, decisions, and preferences from the NEW TRANSCRIPT.
Completely ignore small talk, greetings, filler words, and routine task outputs. But if the user is letting his emotions out or updating about a genral life events(like going on a trip / watching a movie/ completing a game etc...) then KEEP IT..
Do NOT use bullet points. Write a continuous narrative summary.
CRITICAL INSTRUCTION 1: Include the current date [${todayIST}] contextually if recording new events.
CRITICAL INSTRUCTION 2: If the transcript contains raw web search results, news articles, file contents, code blocks, or directory listings (e.g. from local file system tools), COMPLETELY IGNORE THEM. IGNORE  local file changes (creation+deletes) done via MCP server.Do NOT summarize or index web search content or local file outputs. Only index personal facts, goals, and user-specific data.
CRITICAL INSTRUCTION 3: DO NOT REMOVE any thing in which the user has specifically asked GRACE to remember .. Even if its a web search/local file system updates /articles/ etc.... do not remove them ... 
    `;

    for (let i = 0; i < rawBatches.length; i++) {
        if (i > 0) {
            await logToDiscord("[Indexer] Sleeping for 8 seconds to respect the 15 RPM API limit...");
            await sleep(8000);
        }

        await logToDiscord(`[Indexer] Sending Batch ${i + 1} to gemini-2.5-flash-lite for summarization...`);
        try {
            let response;
            let retries = 3;
            while (retries > 0) {
                try {
                    response = await ai.models.generateContent({
                        model: 'gemini-2.5-flash-lite',
                        contents: `${summarizationPrompt}\n\n[NEW TRANSCRIPT]\n${rawBatches[i]}`
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
        await logToDiscord("[Indexer] No meaningful facts were extracted from this session. Skipping Pinecone upsert.");
        return 0;
    }

    // 4. Chunking the CLEAN data with LangChain
    await logToDiscord("[Indexer] Feeding clean summary into LangChain Text Splitter...");
    const splitter = new RecursiveCharacterTextSplitter({
        chunkSize: 400,
        chunkOverlap: 50,
    });

    const documents = await splitter.createDocuments([finalSummaryString]);
    await logToDiscord(`[Indexer] LangChain chopped the summary into ${documents.length} vectors. Starting Deduplication...`);

    // 5. Deduplicate and Upsert
    const newPineconeRecords = [];
    let duplicatesDropped = 0;

    for (let idx = 0; idx < documents.length; idx++) {
        const doc = documents[idx];
        const pineconeRes = await getEmbedding(doc.pageContent, 1);

        let isDuplicate = false;
        if (pineconeRes && pineconeRes.result && pineconeRes.result.hits && pineconeRes.result.hits.length > 0) {
            // Pinecone llama-text-embed-v2 uses 'score' or '_score'. Using 0.35 threshold to drop semantically near-identical duplicates.
            const score = pineconeRes.result.hits[0]._score || pineconeRes.result.hits[0]._score;
            if (score > 0.35) {
                isDuplicate = true;
                duplicatesDropped++;
                console.log(`[Indexer] Chunk ${idx + 1} is a duplicate (score: ${score.toFixed(3)}). Dropping.`);
            }
        }

        if (!isDuplicate) {
            newPineconeRecords.push({
                _id: `chat-memory-${Date.now()}-${idx}`,
                text: doc.pageContent,
                category: "chat_history"
            });
            console.log(`[Indexer] Chunk ${idx + 1} is NEW. Queuing for upsert.`);
        }

        // Small sleep to respect Pinecone embedding API limits if many chunks
        await sleep(500);
    }

    if (newPineconeRecords.length > 0) {
        await upsertQuery(newPineconeRecords);
        await logToDiscord(`[Indexer] Successfully vectorized and stored ${newPineconeRecords.length} NEW high-signal memories in Pinecone!`, true);
    } else {
        await logToDiscord("[Indexer] All chunks were duplicates. Nothing new to store.");
    }

    // 6. Send Notification
    await sendIndexerNotification(finalSummaryString, newPineconeRecords.length, duplicatesDropped);

    return newPineconeRecords.length;
}
