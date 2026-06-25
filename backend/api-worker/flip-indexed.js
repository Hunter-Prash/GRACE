import './env.js';
import { DynamoDBClient } from "@aws-sdk/client-dynamodb";
import { DynamoDBDocumentClient, GetCommand, PutCommand } from "@aws-sdk/lib-dynamodb";

const TABLE_NAME = "GraceChatSessions";
const SESSION_ID = process.argv[2] || "default";

const client = new DynamoDBClient({ region: process.env.AWS_REGION || "ap-south-1" });
const docClient = DynamoDBDocumentClient.from(client);

async function flipIndexed() {
    try {
        console.log(`Fetching session '${SESSION_ID}'...`);
        const response = await docClient.send(new GetCommand({
            TableName: TABLE_NAME,
            Key: { SessionId: SESSION_ID }
        }));

        if (!response.Item || !response.Item.History) {
            console.log("No session found or history is empty.");
            process.exit(0);
        }

        let history = response.Item.History;
        let flippedCount = 0;

        // Flip all messages back to isIndexed = false
        history = history.map(msg => {
            if (msg.isIndexed === true) {
                flippedCount++;
                return { ...msg, isIndexed: false };
            }
            return msg;
        });

        if (flippedCount === 0) {
            console.log("No messages needed flipping (all were already false).");
            process.exit(0);
        }

        console.log(`Flipped ${flippedCount} messages to isIndexed: false. Saving to DynamoDB...`);
        
        await docClient.send(new PutCommand({
            TableName: TABLE_NAME,
            Item: {
                ...response.Item,
                History: history
            }
        }));

        console.log(`\n✅ Success! ${flippedCount} messages were flipped back to UNINDEXED.`);
        console.log("The next time you hit the 40-message limit, these will be sent to Gemini 3.5 Flash Lite for indexing.");
        
    } catch (err) {
        console.error("Failed to flip messages:", err);
    }
}

flipIndexed();
