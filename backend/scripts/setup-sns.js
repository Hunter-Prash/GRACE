import { SNSClient, CreateTopicCommand, SubscribeCommand } from "@aws-sdk/client-sns";
import dotenv from "dotenv";

dotenv.config();

const region = process.env.AWS_REGION || 'us-east-1'; // Defaulting to us-east-1 if not set
const snsClient = new SNSClient({ region: region });

async function setupSns() {
    try {
        console.log(`[SNS Setup] Creating topic 'GraceIndexerTopic' in region ${region}...`);
        
        // 1. Create Topic
        const createTopicCommand = new CreateTopicCommand({
            Name: "GraceIndexerTopic"
        });
        
        const topicResponse = await snsClient.send(createTopicCommand);
        const topicArn = topicResponse.TopicArn;
        
        console.log(`[SNS Setup] Topic created successfully!`);
        console.log(`[SNS Setup] Topic ARN: ${topicArn}`);
        console.log(`[SNS Setup] NOTE: Please add this exact line to your backend/.env file:`);
        console.log(`AWS_SNS_TOPIC_ARN=${topicArn}\n`);

        // 2. Subscribe Email
        const email = "pctechtalks@gmail.com";
        console.log(`[SNS Setup] Subscribing ${email} to the topic...`);
        
        const subscribeCommand = new SubscribeCommand({
            TopicArn: topicArn,
            Protocol: "email",
            Endpoint: email
        });

        await snsClient.send(subscribeCommand);
        console.log(`[SNS Setup] Subscription request sent!`);
        console.log(`[SNS Setup] >>> CRITICAL ACTION REQUIRED: Please check the inbox of ${email} and click 'Confirm Subscription'. Grace cannot send you emails until you do this! <<<`);

    } catch (e) {
        console.error(`[SNS Setup] Failed to setup SNS:`, e);
    }
}

setupSns();
