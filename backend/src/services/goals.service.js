import { PutCommand, ScanCommand, UpdateCommand } from "@aws-sdk/lib-dynamodb";
import { docClient, getISTTimestamp } from './db.client.js';

// Create Grace Goal
export async function createGoal(GoalId, status, category, milestones, description) {
    try {
        const putCommand = new PutCommand({
            TableName: "Grace_Goals",
            Item: {
                GoalId: GoalId,
                Status: status,
                Category: category,
                Milestones: milestones,
                Description: description,
                LastUpdated: getISTTimestamp()
            }
        });
        await docClient.send(putCommand);
    } catch (e) {
        console.warn(`WARNING: Could not create goal: ${e.message}`);
    }
}

// Get active GRACE goals
export async function getActiveGoals() {
    try {
        const scanCommand = new ScanCommand({
            TableName: "Grace_Goals",
            FilterExpression: "#status = :active",
            ExpressionAttributeNames: {
                "#status": "Status" 
            },
            ExpressionAttributeValues: {
                ":active": "Active"
            }
        });
        
        const response = await docClient.send(scanCommand);
        return response.Items || [];
    } catch (e) {
        console.error(`WARNING: Could not fetch goals: ${e.message}`);
        throw e;
    }
}

// Update a specific milestone without overwriting the whole map
export async function updateMilestone(GoalId, milestoneKey, isComplete) {
    try {
        const updateCommand = new UpdateCommand({
            TableName: "Grace_Goals",
            Key: {
                GoalId: GoalId
            },
            UpdateExpression: "SET Milestones.#milestoneKey = :isComplete, LastUpdated = :now",
            ExpressionAttributeNames: {
                "#milestoneKey": milestoneKey
            },
            ExpressionAttributeValues: {
                ":isComplete": isComplete,
                ":now": getISTTimestamp()
            },
            ReturnValues: "ALL_NEW"
        });
        
        const response = await docClient.send(updateCommand);
        const updatedGoal = response.Attributes;
        
        // Auto-complete logic
        if (updatedGoal && updatedGoal.Milestones) {
            const allComplete = Object.values(updatedGoal.Milestones).every(val => val === true);
            if (allComplete && updatedGoal.Status !== "Completed") {
                console.log(`[Goals Engine] All milestones complete for ${GoalId}. Auto-completing goal!`);
                await updateGoalStatus(GoalId, "Completed");
                updatedGoal.Status = "Completed"; 
            }
        }

        return updatedGoal;
    } catch (e) {
        console.error(`WARNING: Could not update milestone: ${e.message}`);
        throw e;
    }
}

// Update the master status of a goal
export async function updateGoalStatus(GoalId, status) {
    try {
        const updateCommand = new UpdateCommand({
            TableName: "Grace_Goals",
            Key: {
                GoalId: GoalId
            },
            UpdateExpression: "SET #status = :status, LastUpdated = :now",
            ExpressionAttributeNames: {
                "#status": "Status"
            },
            ExpressionAttributeValues: {
                ":status": status,
                ":now": getISTTimestamp()
            },
            ReturnValues: "ALL_NEW"
        });
        
        const response = await docClient.send(updateCommand);
        return response.Attributes;
    } catch (e) {
        console.error(`WARNING: Could not update goal status: ${e.message}`);
        throw e;
    }
}
