import { GetCommand, PutCommand } from "@aws-sdk/lib-dynamodb";
import { docClient } from '../services/db.client.js';
import { runMemoryIndexer } from '../jobs/indexer.job.js';
import { logToDiscord } from '../services/logger.service.js';

const TABLE_NAME = "GraceChatSessions";

async function triggerMemoryIndexer(sessionId = "default") {
    try {
        const getCommand = new GetCommand({
            TableName: TABLE_NAME,
            Key: { SessionId: sessionId }
        });
        
        const response = await docClient.send(getCommand);
        if (!response.Item || !response.Item.History) return;

        let history = response.Item.History;
        const unindexedMessages = history.filter(msg => msg.isIndexed === false);

        if (unindexedMessages.length === 0) {
            await logToDiscord("[Lambda Worker] No unindexed messages found in DynamoDB. Aborting.");
            return;
        }

        // Run the Gemini Summarizer + LangChain job
        const chunksIndexed = await runMemoryIndexer(unindexedMessages);
        
        // We MUST mark them as indexed even if chunksIndexed === 0
        // Otherwise, it will enter an infinite loop of triggering every message!
        history = history.map(msg => {
            if (msg.isIndexed === false) {
                return { ...msg, isIndexed: true };
            }
            return msg;
        });

        const putCommand = new PutCommand({
            TableName: TABLE_NAME,
            Item: {
                SessionId: sessionId,
                History: history,
                LastUpdated: response.Item.LastUpdated
            }
        });
        await docClient.send(putCommand);
        await logToDiscord(`[Lambda Worker] Updated DynamoDB. Marked ${unindexedMessages.length} messages as isIndexed: true. (Pinecone chunks: ${chunksIndexed})`);
    } catch (e) {
        console.error(`[Lambda Worker] Indexer Trigger failed: ${e.message}`);
        await logToDiscord(`[Lambda Worker] Indexer Trigger failed: ${e.message}`, true);
        throw e;
    }
}

export const handler = async (event) => {
    console.log("[Lambda] Received EventBridge Event:", JSON.stringify(event, null, 2));

    try {
        // Extract sessionId from the EventBridge detail payload
        const detail = event.detail;
        if (!detail || !detail.sessionId) {
            throw new Error("Missing sessionId in event detail.");
        }

        const sessionId = detail.sessionId;
        await logToDiscord(`[Lambda Worker] Picked up indexer job for session '${sessionId}'...`, true);

        // Execute the heavy memory indexer logic
        await triggerMemoryIndexer(sessionId);

        await logToDiscord(`[Lambda Worker] Successfully completed indexer job for session '${sessionId}'.`);
        
        return {
            statusCode: 200,
            body: JSON.stringify('Indexer executed successfully!'),
        };
    } catch (error) {
        console.error("[Lambda Error]", error);
        await logToDiscord(`[Lambda Worker] FATAL ERROR: ${error.message}`, true);
        throw error; // Let AWS Lambda handle the retry/DLQ if configured
    }
};
