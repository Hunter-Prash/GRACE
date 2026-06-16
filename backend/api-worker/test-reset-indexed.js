// test-reset-indexed.js
// Run from INSIDE api-worker directory:
//   node test-reset-indexed.js [sessionId]

import './env.js';
import { DynamoDBClient } from "@aws-sdk/client-dynamodb";
import { DynamoDBDocumentClient, GetCommand, PutCommand } from "@aws-sdk/lib-dynamodb";

const TABLE_NAME = "GraceChatSessions";
const SESSION_ID = process.argv[2] || "default";
const COUNT = 20; // Number of recent messages to reset

const client = new DynamoDBClient({ region: process.env.AWS_REGION || "ap-south-1" });
const docClient = DynamoDBDocumentClient.from(client);

async function run() {
    console.log(`[RESET] Fetching session: "${SESSION_ID}"...`);
    
    const response = await docClient.send(new GetCommand({
        TableName: TABLE_NAME,
        Key: { SessionId: SESSION_ID }
    }));

    if (!response.Item || !response.Item.History) {
        console.log("No session found or history is empty.");
        process.exit(0);
    }

    const history = response.Item.History;
    
    if (history.length === 0) {
        console.log("History is empty.");
        process.exit(0);
    }

    // Determine how many items to modify (up to COUNT)
    const itemsToModify = Math.min(COUNT, history.length);
    const startIndex = history.length - itemsToModify;

    let modifiedCount = 0;
    for (let i = startIndex; i < history.length; i++) {
        // If it's already false, it stays false. If true/undefined, set to false.
        if (history[i].isIndexed !== false) {
            history[i].isIndexed = false;
            modifiedCount++;
        }
    }

    if (modifiedCount === 0) {
        console.log(`\n✅ The last ${itemsToModify} messages already have isIndexed: false. No updates needed.`);
        process.exit(0);
    }

    console.log(`\n[RESET] Modifying ${modifiedCount} messages to have isIndexed: false...`);

    // Put updated item back
    await docClient.send(new PutCommand({
        TableName: TABLE_NAME,
        Item: response.Item
    }));

    console.log(`✅ Successfully reset ${modifiedCount} messages for session "${SESSION_ID}".`);
    console.log(`Run 'node test-unindexed-count.js ${SESSION_ID}' to verify!`);
}

run().catch(console.error);
