import { GetCommand, PutCommand, DeleteCommand } from "@aws-sdk/lib-dynamodb";
import { docClient, getISTTimestamp } from './db.client.js';
import { triggerIndexerEvent } from './eventbus.service.js';

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
            console.log(`[DB] ${unindexedCount} unindexed messages reached! Publishing EventBridge trigger...`);
            await triggerIndexerEvent(sessionId, unindexedCount);
            return true;
        }
        return false;

    } catch (e) {
        console.warn(`WARNING: Could not save message: ${e.message}`);
    }
}
