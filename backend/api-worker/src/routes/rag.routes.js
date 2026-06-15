import express from 'express';
import { getRagStats } from '../services/rag.service.js';
import { dbMetrics } from '../services/chat.service.js';

const router = express.Router();

router.get('/stats', async (req, res) => {
    try {
        const stats = await getRagStats();
        if (!stats) {
            return res.status(500).json({ error: "Failed to fetch RAG stats" });
        }
        res.json({
            pinecone: stats,
            dynamo: dbMetrics
        });
    } catch (error) {
        console.error("Error in /rag/stats:", error);
        res.status(500).json({ error: "Internal server error", details: error.message });
    }
});

export default router;
