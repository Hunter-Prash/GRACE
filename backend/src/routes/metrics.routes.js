import express from 'express';
import { getDailyMetrics, updateDailyMetrics } from '../services/metrics.service.js';

const router = express.Router();

router.get('/:date', async (req, res) => {
    try {
        const { date } = req.params;
        const metrics = await getDailyMetrics(date);
        
        if (!metrics) {
            return res.status(404).json({ message: "No metrics found for this date" });
        }
        res.json({ metrics });
    } catch (error) {
        console.error("Error in GET /api/metrics/:date:", error);
        res.status(500).json({ error: "Internal server error", details: error.message });
    }
});

router.post('/', async (req, res) => {
    try {
        const { habits, mood_score, energy_lvl, core_focus } = req.body;
        const metrics = await updateDailyMetrics(habits, mood_score, energy_lvl, core_focus);
        res.status(200).json({ message: "Metrics updated successfully", metrics });
    } catch (error) {
        console.error("Error in POST /api/metrics:", error);
        res.status(500).json({ error: "Internal server error", details: error.message });
    }
});

export default router;
