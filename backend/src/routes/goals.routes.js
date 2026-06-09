import express from 'express';
import { createGoal, getActiveGoals, updateMilestone } from '../services/goals.service.js';

const router = express.Router();

router.get('/active', async (req, res) => {
    try {
        const goals = await getActiveGoals();
        res.json({ goals });
    } catch (error) {
        console.error("Error in GET /api/goals/active:", error);
        res.status(500).json({ error: "Internal server error", details: error.message });
    }
});

router.post('/', async (req, res) => {
    try {
        const { goalId, status = "Active", category, milestones = {}, description = "" } = req.body;
        
        if (!goalId) {
            return res.status(400).json({ error: "goalId is required" });
        }

        await createGoal(goalId, status, category, milestones, description);
        
        res.status(201).json({ message: "Goal created successfully", goalId });
    } catch (error) {
        console.error("Error in POST /api/goals:", error);
        res.status(500).json({ error: "Internal server error", details: error.message });
    }
});

router.patch('/:goalId/milestone', async (req, res) => {
    try {
        const { goalId } = req.params;
        const { milestoneKey, isComplete } = req.body;
        
        if (!milestoneKey || typeof isComplete !== 'boolean') {
            return res.status(400).json({ error: "milestoneKey and a boolean isComplete are required" });
        }

        const updatedGoal = await updateMilestone(goalId, milestoneKey, isComplete);
        res.json({ message: "Milestone updated successfully", updatedGoal });
    } catch (error) {
        console.error("Error in PATCH /api/goals/:goalId/milestone:", error);
        res.status(500).json({ error: "Internal server error", details: error.message });
    }
});

export default router;
