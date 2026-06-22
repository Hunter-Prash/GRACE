// test-unindexed-count.js
// Usage: node test-unindexed-count.js [sessionId]
//   sessionId defaults to "default"

import './env.js';
import { DynamoDBClient } from "@aws-sdk/client-dynamodb";
import { DynamoDBDocumentClient, GetCommand } from "@aws-sdk/lib-dynamodb";

const TABLE_NAME = "GraceChatSessions";
const SESSION_ID = process.argv[2] || "default";

const client = new DynamoDBClient({ region: process.env.AWS_REGION || "ap-south-1" });
const docClient = DynamoDBDocumentClient.from(client);

const response = await docClient.send(new GetCommand({
    TableName: TABLE_NAME,
    Key: { SessionId: SESSION_ID }
}));

if (!response.Item || !response.Item.History) {
    console.log("No session found or history is empty.");
    process.exit(0);
}

const history     = response.Item.History;
const total       = history.length;
const unindexed   = history.filter(m => m.isIndexed === false).length;
const indexed     = history.filter(m => m.isIndexed === true).length;
const remaining   = Math.max(0, 40 - unindexed);

console.log(`\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━`);
console.log(`  SESSION       : ${SESSION_ID}`);
console.log(`  LAST UPDATED  : ${response.Item.LastUpdated || "N/A"}`);
console.log(`━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━`);
console.log(`  TOTAL         : ${total}`);
console.log(`  INDEXED       : ${indexed}`);
console.log(`  UNINDEXED     : ${unindexed}  ← (isIndexed === false)`);
console.log(`  UNTIL TRIGGER : ${remaining} msgs left before Lambda fires`);
console.log(`━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n`);
