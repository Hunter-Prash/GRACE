import { DynamoDBClient } from "@aws-sdk/client-dynamodb";
import { DynamoDBDocumentClient, GetCommand, PutCommand } from "@aws-sdk/lib-dynamodb";
import { AWS_REGION } from './config.js';

const client = new DynamoDBClient({ region: AWS_REGION });
const docClient = DynamoDBDocumentClient.from(client);

const TABLE_NAME = "GraceChatSessions";

export async function loadChatHistory(sessionId = "default") {
    try {
        const command = new GetCommand({
            TableName: TABLE_NAME,
            Key: {
                SessionId: sessionId
            }
        });

        const response = await docClient.send(command);
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
            Key: { SessionId: sessionId }
        });
        
        const response = await docClient.send(getCommand);
        let history = (response.Item && response.Item.History) ? response.Item.History : [];
        
        history.push({ role: "user", text: userText });
        history.push({ role: "model", text: graceText });
        
        if (history.length > 50) {
            history = history.slice(-50);
        }
        
        const putCommand = new PutCommand({
            TableName: TABLE_NAME,
            Item: {
                SessionId: sessionId,
                History: history,
                LastUpdated: new Date().toISOString()
            }
        });
        
        await docClient.send(putCommand);
    } catch (e) {
        console.warn(`WARNING: Could not save message: ${e.message}`);
    }
}
