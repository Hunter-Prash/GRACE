import 'dotenv/config';
import express from 'express';
import cors from 'cors';
import chatRoutes from './src/routes/chat.routes.js';
import goalsRoutes from './src/routes/goals.routes.js';
import metricsRoutes from './src/routes/metrics.routes.js';
import { triggerMemoryIndexer } from './src/services/chat.service.js';
import ragRoutes from './src/routes/rag.routes.js';

const app = express();
const PORT = process.env.PORT || 3000;

app.use(cors());
app.use(express.json());

// Mount routers
app.use('/api', chatRoutes);
app.use('/api/goals', goalsRoutes);
app.use('/api/metrics', metricsRoutes);
app.use('/api/rag', ragRoutes);

app.listen(PORT, () => {
    console.log(`GRACE Backend running on http://localhost:${PORT}`);
});
