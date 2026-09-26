import { GetCommand } from "@aws-sdk/lib-dynamodb";
import { docClient } from '../services/db.client.js';
import { Pinecone } from '@pinecone-database/pinecone';

// Keep cache
let healthCache = {
    isHealthy: true,
    lastChecked: 0,
    services: {
        dynamodb: true,
        pinecone: true
    }
};

const CHECK_INTERVAL = 5 * 60 * 1000; // 5 minutes

const checkDynamoDB = async () => {
    try {
        const cmd = new GetCommand({ TableName: "GraceChatSessions", Key: { SessionId: "health-ping" } });
        await docClient.send(cmd);
        return true;
    } catch (err) {
        console.error("DynamoDB health check failed:", err.message);
        return false;
    }
};

const checkPinecone = async () => {
    try {
        const pc = new Pinecone({ apiKey: 'pcsk_5vyAMm_BhH2yg9Y5YbSkPxK3xkorca4wWtdJ3wJLDJvKb94RJu4BaRMiwx8SeYHpcnmf5Q' });
        const idx = pc.index("grace-longterm-memory", "https://grace-longterm-memory-4ev813t.svc.aped-4627-b74a.pinecone.io");
        await idx.describeIndexStats();
        return true;
    } catch (err) {
        console.error("Pinecone health check failed:", err.message);
        return false;
    }
};

const updateHealthCache = async () => {
    const [dynamoUp, pineconeUp] = await Promise.all([checkDynamoDB(), checkPinecone()]);
    healthCache.services.dynamodb = dynamoUp;
    healthCache.services.pinecone = pineconeUp;
    healthCache.isHealthy = dynamoUp && pineconeUp;
    healthCache.lastChecked = Date.now();
};

export const healthCheckMiddleware = async (req, res, next) => {
    const now = Date.now();
    
    // If cache is expired, kick off a background refresh (don't block THIS request)
    if (now - healthCache.lastChecked > CHECK_INTERVAL) {
        // Kick off asynchronously so we don't add latency to the user
        updateHealthCache().catch(console.error);
        
        // Prevent multiple simultaneous checks on first boot
        if (healthCache.lastChecked === 0) {
            healthCache.lastChecked = now; 
        }
    }

    if (!healthCache.isHealthy) {
        return res.status(503).json({
            error: "Service Unavailable",
            message: "One or more core backend services are currently down.",
            details: healthCache.services
        });
    }

    next();
};
