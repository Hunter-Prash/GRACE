import express from 'express';
import { processChat } from '../services/llm.service.js';
import { saveChatMessage, loadChatHistory } from '../services/chat.service.js';

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

router.post('/chat', async (req, res) => {
    try {
        const { text, sessionId = "default" } = req.body;
        
        if (!text) {
            return res.status(400).json({ error: "Text is required" });
        }

        console.log(`[POST /api/chat] User: ${text}`);

        const result = await processChat(sessionId, text);
        
        // Save to DB asynchronously after responding
        saveChatMessage(sessionId, text, result.text).catch(console.error);
        
        console.log(`[POST /api/chat] Grace: ${result.text}`);

        res.json({
            text: result.text,
            inputTokens: result.inputTokens,
            outputTokens: result.outputTokens,
            dbLatencyMs: result.dbLatencyMs,
            dbContextItemsCount: result.dbContextItemsCount
        });

    } catch (error) {
        console.error("Error processing chat:", error);
        res.status(500).json({ error: "Internal server error", details: error.message });
    }
});

export default router;
