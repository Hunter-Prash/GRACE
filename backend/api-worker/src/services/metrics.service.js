import { GetCommand, PutCommand, ScanCommand, UpdateCommand } from "@aws-sdk/lib-dynamodb";
import { docClient, getISTTimestamp } from './db.client.js';


// UPSERT Daily Metrics
export async function updateDailyMetrics(habits, mood_score, energy_lvl, core_focus) {
    try {
        const isoString = getISTTimestamp();
        const todayStr = isoString.split('T')[0]; // Guarantees "YYYY-MM-DD" in IST

        let updateParts = ["#lastUpdated = :now"];
        let expressionAttributeValues = {
            ":now": isoString
        };

        let expressionAttributeNames = {
            "#lastUpdated": "LastUpdated"
        };

        if (habits !== undefined) {
            updateParts.push("#habits = :habits");
            expressionAttributeNames["#habits"] = "Habits";
            expressionAttributeValues[":habits"] = habits;
        }
        if (mood_score !== undefined) {
            updateParts.push("#mood = :mood");
            expressionAttributeNames["#mood"] = "MoodScore";
            expressionAttributeValues[":mood"] = mood_score;
        }
        if (energy_lvl !== undefined) {
            updateParts.push("#energy = :energy");
            expressionAttributeNames["#energy"] = "EnergyLevel";
            expressionAttributeValues[":energy"] = energy_lvl;
        }
        if (core_focus !== undefined) {
            updateParts.push("#focus = :focus");
            expressionAttributeNames["#focus"] = "CoreFocus";
            expressionAttributeValues[":focus"] = core_focus;
        }

        const params = {
            TableName: "Grace_DailyMetrics",
            Key: { Date: todayStr },
            UpdateExpression: "SET " + updateParts.join(", "),
            ExpressionAttributeValues: expressionAttributeValues,
            ExpressionAttributeNames: expressionAttributeNames,
            ReturnValues: "ALL_NEW"
        };

        const response = await docClient.send(new UpdateCommand(params));
        return response.Attributes;
    } catch (e) {
        console.error(`WARNING: Could not update daily metrics: ${e.message}`);
        throw e;
    }
}

export async function getDailyMetrics() {
    try {
        // Default to today if no date is passed
        const targetDate = getISTTimestamp().split('T')[0];

        const params = {
            TableName: "Grace_DailyMetrics",
            Key: {
                Date: targetDate
            }
        }
        const response = await docClient.send(new GetCommand(params));
        return response.Item || null;
    } catch (e) {
        console.error(`WARNING: Could not fetch daily metrics: ${e.message}`);
        throw e;
    }
}

export async function getAllDailyMetrics() {
    try {
        const params = {
            TableName: "Grace_DailyMetrics"
        };
        // Scan the table. Note: If the table gets very large, this may need pagination.
        const response = await docClient.send(new ScanCommand(params));
        
        let items = response.Items || [];
        // Sort by Date descending (newest first)
        items.sort((a, b) => {
            const dateA = a.Date || "";
            const dateB = b.Date || "";
            return dateB.localeCompare(dateA);
        });
        
        // Return only the last 5 days
        return items.slice(0, 5);
    } catch (e) {
        console.error(`WARNING: Could not fetch all daily metrics: ${e.message}`);
        throw e;
    }
}