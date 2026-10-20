import { UpdateCommand, QueryCommand } from "@aws-sdk/lib-dynamodb";
import { docClient } from './db.client.js';

// Helper: Get IST Date String (YYYY-MM-DD), with support for relative words and past dates
export function getISTDateString(dateInput) {
    const pad = (n) => n < 10 ? '0' + n : n;
    const now = new Date();
    const currentIstMs = now.getTime() + (5.5 * 60 * 60 * 1000);

    if (!dateInput) {
        const istTime = new Date(currentIstMs);
        return istTime.getUTCFullYear() + '-' + pad(istTime.getUTCMonth() + 1) + '-' + pad(istTime.getUTCDate());
    }

    if (typeof dateInput === 'string') {
        const trimmed = dateInput.trim();
        const lower = trimmed.toLowerCase();

        if (lower === 'today') {
            const istTime = new Date(currentIstMs);
            return istTime.getUTCFullYear() + '-' + pad(istTime.getUTCMonth() + 1) + '-' + pad(istTime.getUTCDate());
        }

        if (lower === 'yesterday') {
            const istTime = new Date(currentIstMs - (24 * 60 * 60 * 1000));
            return istTime.getUTCFullYear() + '-' + pad(istTime.getUTCMonth() + 1) + '-' + pad(istTime.getUTCDate());
        }

        const daysAgoMatch = lower.match(/^(\d+)\s+days?\s+ago$/i);
        if (daysAgoMatch) {
            const days = parseInt(daysAgoMatch[1], 10);
            const istTime = new Date(currentIstMs - (days * 24 * 60 * 60 * 1000));
            return istTime.getUTCFullYear() + '-' + pad(istTime.getUTCMonth() + 1) + '-' + pad(istTime.getUTCDate());
        }

        // Direct YYYY-MM-DD
        if (/^\d{4}-\d{2}-\d{2}$/.test(trimmed)) {
            return trimmed;
        }

        const parsed = new Date(trimmed);
        if (!isNaN(parsed.getTime())) {
            const istTime = new Date(parsed.getTime() + (5.5 * 60 * 60 * 1000));
            return istTime.getUTCFullYear() + '-' + pad(istTime.getUTCMonth() + 1) + '-' + pad(istTime.getUTCDate());
        }
    }

    if (dateInput instanceof Date && !isNaN(dateInput.getTime())) {
        const istTime = new Date(dateInput.getTime() + (5.5 * 60 * 60 * 1000));
        return istTime.getUTCFullYear() + '-' + pad(istTime.getUTCMonth() + 1) + '-' + pad(istTime.getUTCDate());
    }

    const istTime = new Date(currentIstMs);
    return istTime.getUTCFullYear() + '-' + pad(istTime.getUTCMonth() + 1) + '-' + pad(istTime.getUTCDate());
}

// Helper: Normalize exercise name (lowercase, replace spaces/special chars with hyphens)
function normalizeExercise(rawName) {
    return rawName.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '');
}

/**
 * 1. Log a Workout Set
 * Uses UpdateItem with list_append to add a new set to an exercise.
 * Supports saving progress for today or a specific past date (e.g. yesterday, DX).
 */
export async function logWorkoutSet(rawExerciseName, reps, weight, targetDate) {
    const exerciseName = normalizeExercise(rawExerciseName);
    const dateStr = getISTDateString(targetDate);
    const todayStr = getISTDateString();

    const timestamp = (dateStr === todayStr)
        ? new Date().toISOString()
        : `${dateStr}T12:00:00.000+05:30`;

    const newSet = { reps: reps, weight: weight, timestamp: timestamp };

    const command = new UpdateCommand({
        TableName: "Grace_Workouts",
        Key: {
            Date: dateStr,
            ExerciseName: exerciseName
        },
        // if_not_exists creates an empty list [] if the Sets column doesn't exist yet
        UpdateExpression: "SET #sets = list_append(if_not_exists(#sets, :empty_list), :new_set)",
        ExpressionAttributeNames: {
            "#sets": "Sets"
        },
        ExpressionAttributeValues: {
            ":empty_list": [],
            ":new_set": [newSet]
        },
        ReturnValues: "ALL_NEW"
    });

    try {
        const response = await docClient.send(command);
        return {
            success: true,
            date: dateStr,
            normalizedExercise: exerciseName, // Return the fixed name so Grace knows what it was saved as
            data: response.Attributes
        };
    } catch (e) {
        console.error("Error logging workout set:", e);
        throw e;
    }
}

/**
 * 2. Get Workout For Date (defaults to Today)
 * Queries the main table for all exercises on the specified date or current IST date.
 */
export async function getTodaysWorkout(targetDate) {
    const dateStr = getISTDateString(targetDate);

    const command = new QueryCommand({
        TableName: "Grace_Workouts",
        KeyConditionExpression: "#d = :date",
        ExpressionAttributeNames: {
            "#d": "Date"
        },
        ExpressionAttributeValues: {
            ":date": dateStr
        }
    });

    try {
        const response = await docClient.send(command);
        const items = response.Items || [];
        items.date = dateStr;
        return items;
    } catch (e) {
        console.error("Error fetching workout for date:", dateStr, e);
        throw e;
    }
}

/**
 * 3. Get Exercise History
 * Queries the Global Secondary Index to show progress for a specific lift over time.
 */
export async function getExerciseHistory(rawExerciseName) {
    const exerciseName = normalizeExercise(rawExerciseName);

    const command = new QueryCommand({
        TableName: "Grace_Workouts",
        IndexName: "ExerciseHistoryIndex",
        KeyConditionExpression: "ExerciseName = :ex",
        ExpressionAttributeValues: {
            ":ex": exerciseName
        },
        ScanIndexForward: false // Sort descending by Date (newest sessions first)
    });

    try {
        const response = await docClient.send(command);
        return {
            normalizedExercise: exerciseName,
            history: response.Items || []
        };
    } catch (e) {
        console.error("Error fetching exercise history:", e);
        throw e;
    }
}