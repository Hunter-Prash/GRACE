import { PutCommand, QueryCommand, UpdateCommand } from "@aws-sdk/lib-dynamodb";
import { docClient, getISTTimestamp } from './db.client.js';

const TABLE_NAME = "Grace_BrainDump";
const DEFAULT_USER = "prashant";

/**
 * Saves a quick thought, note, or reminder to DynamoDB.
 */
export async function saveBrainDump(content, category = "Personal", dueDate = null, tags = []) {
    try {
        const timestamp = getISTTimestamp();
        const noteId = `bd_${Date.now()}`;

        const item = {
            UserId: DEFAULT_USER,
            CreatedAt: timestamp,
            NoteId: noteId,
            Content: content,
            Category: category,
            DueDate: dueDate,
            Tags: Array.isArray(tags) ? tags : [],
            Status: "Active",
            SurfacedCount: 0,
            LastUpdated: timestamp
        };

        const putCommand = new PutCommand({
            TableName: TABLE_NAME,
            Item: item
        });

        await docClient.send(putCommand);
        console.log(`[BrainDump] Saved note [${category}]: "${content.substring(0, 40)}..."`);
        return { success: true, note: item };
    } catch (e) {
        console.error(`[BrainDump] Failed to save note: ${e.message}`);
        throw e;
    }
}

/**
 * Retrieves recent active notes for Prashant from DynamoDB.
 */
export async function getBrainDumpNotes(status = "Active", category = null, limit = 10) {
    try {
        const queryParams = {
            TableName: TABLE_NAME,
            KeyConditionExpression: "UserId = :userId",
            ExpressionAttributeValues: {
                ":userId": DEFAULT_USER
            },
            ScanIndexForward: false, // Newest first
            Limit: limit
        };

        if (status) {
            queryParams.FilterExpression = "#status = :status";
            queryParams.ExpressionAttributeNames = { "#status": "Status" };
            queryParams.ExpressionAttributeValues[":status"] = status;
        }

        if (category) {
            const catExpr = "#cat = :cat";
            queryParams.FilterExpression = queryParams.FilterExpression 
                ? `${queryParams.FilterExpression} AND ${catExpr}`
                : catExpr;
            queryParams.ExpressionAttributeNames = {
                ...(queryParams.ExpressionAttributeNames || {}),
                "#cat": "Category"
            };
            queryParams.ExpressionAttributeValues[":cat"] = category;
        }

        const response = await docClient.send(new QueryCommand(queryParams));
        return response.Items || [];
    } catch (e) {
        console.error(`[BrainDump] Failed to fetch notes: ${e.message}`);
        return [];
    }
}

/**
 * Marks a specific note as Completed or Archived.
 */
export async function updateBrainDumpStatus(createdAt, status = "Completed") {
    try {
        const updateCommand = new UpdateCommand({
            TableName: TABLE_NAME,
            Key: {
                UserId: DEFAULT_USER,
                CreatedAt: createdAt
            },
            UpdateExpression: "SET #status = :status, LastUpdated = :updated",
            ExpressionAttributeNames: {
                "#status": "Status"
            },
            ExpressionAttributeValues: {
                ":status": status,
                ":updated": getISTTimestamp()
            }
        });

        await docClient.send(updateCommand);
        console.log(`[BrainDump] Updated note at ${createdAt} to status ${status}`);
        return { success: true };
    } catch (e) {
        console.error(`[BrainDump] Failed to update note status: ${e.message}`);
        throw e;
    }
}

/**
 * Fetches active notes that have an upcoming or today due date.
 */
export async function getDueBrainDumps() {
    try {
        const activeNotes = await getBrainDumpNotes("Active", null, 30);
        const todayDateStr = getISTTimestamp().split("T")[0]; // YYYY-MM-DD in IST

        return activeNotes.filter(n => {
            if (!n.DueDate) return false;
            // Check if DueDate contains today's date or is upcoming
            return n.DueDate.includes(todayDateStr) || n.DueDate <= todayDateStr;
        });
    } catch (e) {
        console.error(`[BrainDump] Failed to fetch due notes: ${e.message}`);
        return [];
    }
}

