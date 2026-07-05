import { QueryCommand, PutCommand } from "@aws-sdk/lib-dynamodb";
import { docClient } from './db.client.js';
import crypto from 'crypto';

const TABLE_NAME = "Expense-Tracker-Transactions-Table";
const USER_ID = "d3de2293-409d-415f-8b59-0b3ac6cd31b5";

export const ALLOWED_CATEGORIES = [
    "essentials", "entertainment", "transport", "career", "income"
];

export async function getTransactions(startDate, endDate) {
    const params = {
        TableName: TABLE_NAME,
        KeyConditionExpression: "user_id = :uid AND transaction_date BETWEEN :start AND :end",
        ExpressionAttributeValues: {
            ":uid": USER_ID,
            ":start": startDate,
            ":end": endDate
        }
    };
    try {
        const response = await docClient.send(new QueryCommand(params));
        return response.Items;
    } catch (error) {
        console.error("Error fetching transactions:", error);
        throw error;
    }
}

export async function addTransaction(amount, categoryName, description) {
    const catName = categoryName.toLowerCase();
    if (!ALLOWED_CATEGORIES.includes(catName)) {
        throw new Error(`Invalid category: ${categoryName}. Must be one of: ${ALLOWED_CATEGORIES.join(', ')}`);
    }

    const transactionId = crypto.randomUUID();
    const timestamp = new Date(new Date().getTime() + 5.5 * 60 * 60 * 1000).toISOString().replace('Z', '+05:30');

    const params = {
        TableName: TABLE_NAME,
        Item: {
            user_id: USER_ID,
            transaction_date: timestamp,
            id: transactionId,
            amount: parseFloat(amount),
            category_name: catName,
            created_at: timestamp,
            description: description || ""
        }
    };

    try {
        await docClient.send(new PutCommand(params));
        return {
            id: transactionId,
            message: "Transaction added successfully."
        };
    } catch (error) {
        console.error("Error adding transaction:", error);
        throw error;
    }
}
