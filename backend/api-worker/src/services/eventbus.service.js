import { EventBridgeClient, PutEventsCommand } from "@aws-sdk/client-eventbridge";
import dotenv from 'dotenv';
import { logToDiscord } from './logger.service.js';
import { getISTTimestamp } from './db.client.js';

dotenv.config();

const client = new EventBridgeClient({ region: process.env.AWS_REGION });

export const triggerIndexerEvent = async (sessionId, unindexedCount) => {
    try {
        const eventBusName = process.env.AWS_EVENT_BUS_NAME || "grace-ai-bus";

        const params = {
            Entries: [
                {
                    Source: "grace.chat.service",
                    DetailType: "MemoryBatchReady",
                    Detail: JSON.stringify({
                        sessionId: sessionId,
                        unindexedCount: unindexedCount,
                        timestamp: getISTTimestamp()
                    }),
                    EventBusName: eventBusName
                }
            ]
        };

        const command = new PutEventsCommand(params);
        await client.send(command);
        
        await logToDiscord(`[EventBridge] Published 'MemoryBatchReady' event for session '${sessionId}' to bus '${eventBusName}'.`);
        return true;
    } catch (error) {
        console.error("[EventBridge] Failed to publish event:", error.message);
        await logToDiscord(`[EventBridge Error] Failed to trigger indexer: ${error.message}`, true);
        return false;
    }
};
