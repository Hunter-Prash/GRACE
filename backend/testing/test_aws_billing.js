import dotenv from 'dotenv';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
dotenv.config({ path: path.resolve(__dirname, '../.env') });

import { getLastMonthBill, getMonthToDateSpend, getAwsCostReport, syncMonthlyAwsBillToBrainDump, markAwsBillAsPaid } from '../api-worker/src/services/awsCost.service.js';
import { processChat } from '../api-worker/src/services/llm.service.js';

async function runTests() {
    console.log("=================================================");
    console.log("TEST 1: Direct AWS Cost Explorer Service Tests");
    console.log("=================================================");

    const lastMonth = await getLastMonthBill();
    console.log("Last Month Bill:", lastMonth);

    const mtd = await getMonthToDateSpend();
    console.log("Month-to-Date Spend:", mtd);

    const report = await getAwsCostReport();
    console.log("Full Cost Report:", JSON.stringify(report, null, 2));

    console.log("\n=================================================");
    console.log("TEST 2: Sync Bill to BrainDump (Existing Table)");
    console.log("=================================================");

    const syncResult = await syncMonthlyAwsBillToBrainDump();
    console.log("Sync Result:", syncResult);

    console.log("\n=================================================");
    console.log("TEST 3: LLM Chat Query: 'What is my AWS bill?'");
    console.log("=================================================");

    const chatRes1 = await processChat("test-aws-cost-" + Date.now(), "Grace, what's my AWS bill right now and for last month?");
    console.log("Tools invoked:", chatRes1.toolsUsed);
    console.log("Grace's Response:\n", chatRes1.text);

    if (!chatRes1.toolsUsed.includes("getAwsCostReport")) {
        throw new Error("Grace failed to call getAwsCostReport!");
    }

    console.log("\n=================================================");
    console.log("TEST 4: Mark Bill As Paid");
    console.log("=================================================");

    const paidResult = await markAwsBillAsPaid();
    console.log("Mark as Paid Result:", paidResult);

    console.log("\n=================================================");
    console.log("TEST 5: LLM Chat: 'I paid the AWS bill'");
    console.log("=================================================");

    const chatRes2 = await processChat("test-aws-paid-" + Date.now(), "Grace, I just paid the AWS bill.");
    console.log("Tools invoked:", chatRes2.toolsUsed);
    console.log("Grace's Response:\n", chatRes2.text);

    if (!chatRes2.toolsUsed.includes("markAwsBillPaid")) {
        throw new Error("Grace failed to call markAwsBillPaid!");
    }

    console.log("\n✓ All AWS Billing tests passed successfully!");
    process.exit(0);
}

runTests().catch(err => {
    console.error("Test execution failed:", err);
    process.exit(1);
});
