import express from 'express';
import cors from 'cors';
import chatRoutes from './src/routes/chat.routes.js';
import goalsRoutes from './src/routes/goals.routes.js';
import metricsRoutes from './src/routes/metrics.routes.js';
import ragRoutes from './src/routes/rag.routes.js';
import authRoutes from './src/routes/auth.routes.js';
import { verifyToken } from './src/middleware/auth.js';
import { healthCheckMiddleware } from './src/middleware/healthCheck.js';

const app = express();

app.use(cors());
app.use(express.json());

// Apply health check middleware to all /api routes
app.use('/api', healthCheckMiddleware);

// Mount routers
app.use('/api/auth', authRoutes);

// Protect the following routes
app.use('/api', verifyToken, chatRoutes);
app.use('/api/goals', verifyToken, goalsRoutes);
app.use('/api/metrics', verifyToken, metricsRoutes);
app.use('/api/rag', verifyToken, ragRoutes);

app.get('/health', (req, res) => {
    res.status(200).json({ status: 'healthy', service: 'api-worker' });
});

export default app;
