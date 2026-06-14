import { GetCommand, PutCommand, DeleteCommand } from "@aws-sdk/lib-dynamodb";
import { docClient, getISTTimestamp } from './db.client.js';
import { runMemoryIndexer } from '../jobs/indexer.job.js';

const TABLE_NAME = "GraceChatSessions";

export let dbMetrics = {
    rcu: 0,
    wcu: 0
};

export async function loadChatHistory(sessionId = "default") {
    try {
        const command = new GetCommand({
            TableName: TABLE_NAME,
            Key: {
                SessionId: sessionId
            },
            ReturnConsumedCapacity: "TOTAL"
        });

        const response = await docClient.send(command);
        if (response.ConsumedCapacity) {
            dbMetrics.rcu += response.ConsumedCapacity.CapacityUnits;
        }
        const item = response.Item;

        if (!item || !item.History) {
            return [];
        }

        const history = [];
        for (const msg of item.History) {
            history.push({
                role: msg.role,
                parts: [{ text: msg.text || "" }]
            });
        }
        return history;
    } catch (e) {
        console.warn(`WARNING: Could not load chat history: ${e.message}`);
        return [];
    }
}

export async function saveChatMessage(sessionId, userText, graceText) {
    try {
        const getCommand = new GetCommand({
            TableName: TABLE_NAME,
            Key: { SessionId: sessionId },
            ReturnConsumedCapacity: "TOTAL"
        });

        const response = await docClient.send(getCommand);
        if (response.ConsumedCapacity) {
            dbMetrics.rcu += response.ConsumedCapacity.CapacityUnits;
        }
        let history = (response.Item && response.Item.History) ? response.Item.History : [];

        history.push({ role: "user", text: userText, isIndexed: false });
        history.push({ role: "model", text: graceText, isIndexed: false });

        // Maintain the 50-message context window to prevent DynamoDB bloat
        if (history.length > 50) {
            history = history.slice(-50);
        }

        const putCommand = new PutCommand({
            TableName: TABLE_NAME,
            Item: {
                SessionId: sessionId,
                History: history,
                LastUpdated: getISTTimestamp()
            },
            ReturnConsumedCapacity: "TOTAL"
        });

        const putResponse = await docClient.send(putCommand);
        if (putResponse.ConsumedCapacity) {
            dbMetrics.wcu += putResponse.ConsumedCapacity.CapacityUnits;
        }

        // --- THE DUAL TRIGGER SYSTEM (TRIGGER 1: Message Count) ---
        // If they are rapid-firing messages and hit 40 unindexed, trigger immediately 
        // to prevent them from falling out of the 50-message context window.
        const unindexedCount = history.filter(m => m.isIndexed === false).length;
        if (unindexedCount >= 40) {
            console.log("[DB] 40 unindexed messages reached! Triggering emergency indexer...");
            triggerMemoryIndexer(sessionId).catch(console.error);
            return true;
        }
        return false;

    } catch (e) {
        console.warn(`WARNING: Could not save message: ${e.message}`);
    }
}

export async function triggerMemoryIndexer(sessionId = "default") {
    try {
        const getCommand = new GetCommand({
            TableName: TABLE_NAME,
            Key: { SessionId: sessionId }
        });
        
        const response = await docClient.send(getCommand);
        if (!response.Item || !response.Item.History) return;

        let history = response.Item.History;
        const unindexedMessages = history.filter(msg => msg.isIndexed === false);

        if (unindexedMessages.length === 0) return;

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
        console.log(`[DB] Marked ${unindexedMessages.length} messages as isIndexed: true. (Pinecone chunks: ${chunksIndexed})`);
    } catch (e) {
        console.error(`[DB] Indexer Trigger failed: ${e.message}`);
    }
}

