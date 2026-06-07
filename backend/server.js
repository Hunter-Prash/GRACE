import express from 'express';
import cors from 'cors';
import { processChat } from './src/llm.js';
import { saveChatMessage, loadChatHistory } from './src/db.js';

const app = express();
const PORT = process.env.PORT || 3000;

app.use(cors());
app.use(express.json());

app.get('/api/history/:sessionId', async (req, res) => {
    try {
        const history = await loadChatHistory(req.params.sessionId);
        res.json(history);
    } catch (error) {
        console.error("Error fetching history:", error);
        res.status(500).json({ error: "Internal server error", details: error.message });
    }
});

app.post('/api/chat', async (req, res) => {
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
            outputTokens: result.outputTokens
        });

    } catch (error) {
        console.error("Error processing chat:", error);
        res.status(500).json({ error: "Internal server error", details: error.message });
    }
});

app.listen(PORT, () => {
    console.log(`GRACE Backend running on http://localhost:${PORT}`);
});
