import express from 'express';
import { processChat } from '../services/llm.service.js';
import { saveChatMessage, loadChatHistory, triggerMemoryIndexer } from '../services/chat.service.js';
import { clearChatHistory, clearAllMemory, wipePinecone } from '../services/memory.service.js';

const router = express.Router();

router.get('/history/:sessionId', async (req, res) => {
    try {
        const dbStart = performance.now();
        const history = await loadChatHistory(req.params.sessionId);
        const dbLatencyMs = Math.round(performance.now() - dbStart);
        res.json({
            history: history,
            dbLatencyMs: dbLatencyMs,
            dbContextItemsCount: history.length
        });
    } catch (error) {
        console.error("Error fetching history:", error);
        res.status(500).json({ error: "Internal server error", details: error.message });
    }
});

router.delete('/history/:sessionId', async (req, res) => {
    try {
        await clearChatHistory(req.params.sessionId);
        res.json({ success: true, message: "Chat history cleared" });
    } catch (error) {
        console.error("Error clearing history:", error);
        res.status(500).json({ error: "Internal server error", details: error.message });
    }
});

router.delete('/memory/:sessionId', async (req, res) => {
    try {
        await clearAllMemory(req.params.sessionId);
        res.json({ success: true, message: "All short-term and long-term memory cleared" });
    } catch (error) {
        console.error("Error clearing all memory:", error);
        res.status(500).json({ error: "Internal server error", details: error.message });
    }
});

router.delete('/pinecone', async (req, res) => {
    try {
        await wipePinecone();
        res.json({ success: true, message: "Pinecone long-term memory cleared" });
    } catch (error) {
        console.error("Error clearing Pinecone memory:", error);
        res.status(500).json({ error: "Internal server error", details: error.message });
    }
});

router.post('/chat', async (req, res) => {
    try {
        const { text, sessionId = "default" } = req.body;

        if (!text) {
            return res.status(400).json({ error: "Text is required" });
        }

        const result = await processChat(sessionId, text);

        // Save to DB and check if it triggered the memory indexer
        const indexerTriggered = await saveChatMessage(sessionId, text, result.text);

        res.json({
            text: result.text,
            inputTokens: result.inputTokens,
            outputTokens: result.outputTokens,
            dbLatencyMs: result.dbLatencyMs,
            dbContextItemsCount: result.dbContextItemsCount,
            toolsUsed: result.toolsUsed,
            indexerTriggered: indexerTriggered
        });

    } catch (error) {
        console.error("Error processing chat:", error);
        res.status(500).json({ error: "Internal server error", details: error.message });
    }
});

// For testing purposes: Force the RAG indexer to run immediately without waiting 15 mins
router.get('/trigger-indexer', async (req, res) => {
    try {
        console.log("[DEBUG] Manual indexer trigger requested...");
        await triggerMemoryIndexer("default");
        res.json({ message: 'Indexer trigger executed successfully.' });
    } catch (error) {
        console.error(error);
        res.status(500).json({ error: 'Failed to trigger indexer' });
    }
});

export default router;
