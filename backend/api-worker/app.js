import express from 'express';
import cors from 'cors';
import chatRoutes from './src/routes/chat.routes.js';
import goalsRoutes from './src/routes/goals.routes.js';
import metricsRoutes from './src/routes/metrics.routes.js';
import ragRoutes from './src/routes/rag.routes.js';

const app = express();

app.use(cors());
app.use(express.json());

// Mount routers
app.use('/api', chatRoutes);
app.use('/api/goals', goalsRoutes);
app.use('/api/metrics', metricsRoutes);
app.use('/api/rag', ragRoutes);

app.get('/health', (req, res) => {
    res.status(200).json({ status: 'healthy', service: 'api-worker' });
});

export default app;
