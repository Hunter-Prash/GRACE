import { DynamoDBClient } from "@aws-sdk/client-dynamodb";
import { DynamoDBDocumentClient } from "@aws-sdk/lib-dynamodb";
import { AWS_REGION } from '../config.js';

const client = new DynamoDBClient({ region: AWS_REGION });
export const docClient = DynamoDBDocumentClient.from(client);

// Helper to get exact IST timestamp in ISO format
export const getISTTimestamp = () => {
    return new Date(new Date().getTime() + 5.5 * 60 * 60 * 1000).toISOString().replace('Z', '+05:30');
};
