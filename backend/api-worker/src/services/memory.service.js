import { DeleteCommand } from "@aws-sdk/lib-dynamodb";
import { docClient } from './db.client.js';
import { clearPineconeMemory } from './rag.service.js';

const TABLE_NAME = "GraceChatSessions";

export async function clearChatHistory(sessionId = "default") {
    try {
        const deleteCommand = new DeleteCommand({
            TableName: TABLE_NAME,
            Key: { SessionId: sessionId }
        });
        await docClient.send(deleteCommand);
        console.log(`[DB] Erased short-term history for session: ${sessionId}`);
    } catch (e) {
        console.error(`ERROR: Could not clear chat history: ${e.message}`);
        throw e;
    }
}

export async function wipePinecone() {
    try {
        await clearPineconeMemory();
        console.log("[Memory] Wiped long-term Pinecone context.");
    } catch (e) {
        console.error(`ERROR: Failed to wipe Pinecone: ${e.message}`);
        throw e;
    }
}

export async function clearAllMemory(sessionId = "default") {
    try {
        // 1. Wipe short-term DynamoDB context
        await clearChatHistory(sessionId);
        
        // 2. Wipe long-term Pinecone context
        await clearPineconeMemory();
        
        console.log("[Memory] Completely wiped all Short-Term and Long-Term Memory.");
    } catch (e) {
        console.error(`ERROR: Failed to wipe all memory: ${e.message}`);
        throw e;
    }
}
