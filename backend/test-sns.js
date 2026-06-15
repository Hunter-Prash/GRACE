import { sendIndexerNotification } from "./src/services/sns.service.js";

async function testSNS() {
    console.log("Testing SNS Email Delivery...");
    const dummySummary = "Prashant successfully integrated Amazon SNS into the Grace Life OS! He securely configured IAM credentials for ap-south-1 and automated topic subscription. The system is now capable of delivering daily memory digests directly to pctechtalks@gmail.com.";
    
    await sendIndexerNotification(dummySummary, 2, 1);
    console.log("Done!");
}

testSNS();
