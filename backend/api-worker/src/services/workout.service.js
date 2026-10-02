import { UpdateCommand, QueryCommand } from "@aws-sdk/lib-dynamodb";
import { docClient } from './db.client.js';
import stringSimilarity from 'string-similarity';

// List of standard exercises for fuzzy matching
const KNOWN_EXERCISES = [
    "squat",
    "bench-press",
    "barbell-row",
    "pull-up",
    "overhead-press",
    "romanian-deadlift",
    "plank",
    "hanging-leg-raise",
    "deadlift",
    "incline-bench-press",
    "lat-pulldown",
    "chin-up",
    "leg-press",
    "bulgarian-split-squat",
    "shoulder-press",
    "lateral-raise",
    "cable-crunch",
    "ab-wheel",
    // Extras for standard coverage
    "bicep-curl",
    "tricep-extension",
    "push-up",
    "dumbbell-row"
];

// Helper: Get current IST Date String (YYYY-MM-DD)
function getISTDateString() {
    const now = new Date();
    const istTime = new Date(now.getTime() + (5.5 * 60 * 60 * 1000));
    const pad = (n) => n < 10 ? '0' + n : n;
    return istTime.getUTCFullYear() + '-' + pad(istTime.getUTCMonth() + 1) + '-' + pad(istTime.getUTCDate());
}

// Helper: Normalize exercise name using fuzzy matching
function normalizeExercise(rawName) {
    // 1. Basic cleaning (lowercase, replace spaces/special chars with hyphens)
    const cleaned = rawName.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '');

    // 2. Fuzzy match against known exercises
    const matches = stringSimilarity.findBestMatch(cleaned, KNOWN_EXERCISES);

    // If the best match is >= 60% similar, use the standard name
    if (matches.bestMatch.rating >= 0.6) {
        return matches.bestMatch.target;
    }

    // Fallback: If it's a completely new exercise, just return the cleaned version
    return cleaned;
}

/**
 * 1. Log a Workout Set
 * Uses UpdateItem with list_append to add a new set to an exercise.
 * If the exercise doesn't exist for today, it creates it.
 */
export async function logWorkoutSet(rawExerciseName, reps, weight) {
    const exerciseName = normalizeExercise(rawExerciseName);
    const dateStr = getISTDateString();

    const newSet = { reps: reps, weight: weight, timestamp: new Date().toISOString() };

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
            normalizedExercise: exerciseName, // Return the fixed name so Grace knows what it was saved as
            data: response.Attributes
        };
    } catch (e) {
        console.error("Error logging workout set:", e);
        throw e;
    }
}

/**
 * 2. Get Today's Workout
 * Queries the main table for all exercises on the current IST date.
 */
export async function getTodaysWorkout() {
    const dateStr = getISTDateString();

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
        return response.Items || [];
    } catch (e) {
        console.error("Error fetching today's workout:", e);
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
