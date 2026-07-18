import { SNSClient, PublishCommand } from "@aws-sdk/client-sns";
import dotenv from "dotenv";

dotenv.config();

const region = process.env.AWS_REGION || 'ap-south-1';
const snsClient = new SNSClient({ region: region });

export const sendIndexerNotification = async (summary, newRecordsCount, duplicateCount) => {
    try {
        const topicArn = process.env.AWS_SNS_TOPIC_ARN;
        if (!topicArn) {
            console.warn("[SNS] Warning: AWS_SNS_TOPIC_ARN not found in .env. Skipping notification.");
            return;
        }

        const dateStr = new Date().toLocaleString('en-US', { timeZone: 'Asia/Kolkata' });

        const messageBody = `
Grace Memory Indexer Complete
================================
Time: ${dateStr}

Pinecone Stats:
- New Memories Saved: ${newRecordsCount}
- Duplicates Dropped: ${duplicateCount}

Today's Memory Summary:
--------------------------------
${summary}

================================
This is an automated digest from the Grace Life OS.
        `.trim();

        const publishCommand = new PublishCommand({
            TopicArn: topicArn,
            Subject: "Grace Memory Indexer Daily Digest",
            Message: messageBody
        });

        await snsClient.send(publishCommand);
        console.log(`[SNS] Successfully sent indexer digest email to Topic!`);
    } catch (error) {
        console.error("[SNS] Error sending indexer notification:", error);
    }
};
