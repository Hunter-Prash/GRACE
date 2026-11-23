import dotenv from 'dotenv';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
dotenv.config({ path: path.resolve(__dirname, '../.env') });

import { evaluateImpulseSpend } from '../api-worker/src/services/finance.service.js';
import { processChat } from '../api-worker/src/services/llm.service.js';

async function runTests() {
    console.log("=================================================");
    console.log("TEST 1: Direct evaluateImpulseSpend unit tests");
    console.log("=================================================");

    // Case 1: High-impact spend
    const monitor = await evaluateImpulseSpend("34-inch Curved Gaming Monitor", 16000, "entertainment", 65000);
    console.log("16k Monitor Result:", {
        item: monitor.itemName,
        cost: monitor.cost,
        hours: monitor.hoursOfLaborRequired,
        workDays: monitor.workDaysEquivalent,
        verdict: monitor.verdict,
        cooldownDays: monitor.coolingOffDaysRecommended,
        headline: monitor.realityCheckHeadline
    });

    if (monitor.coolingOffDaysRecommended !== 7) {
        throw new Error(`Expected 7 days cooldown for 16k spend, got ${monitor.coolingOffDaysRecommended}`);
    }
    if (monitor.verdict !== "HIGH_IMPACT_SPEND") {
        throw new Error(`Expected HIGH_IMPACT_SPEND, got ${monitor.verdict}`);
    }
    console.log("✓ Test 1A (High Impact) Passed!");

    // Case 2: Moderate-impact spend
    const keyboard = await evaluateImpulseSpend("Mechanical Keyboard", 3500, "entertainment", 65000);
    console.log("3.5k Keyboard Result:", {
        item: keyboard.itemName,
        cost: keyboard.cost,
        hours: keyboard.hoursOfLaborRequired,
        workDays: keyboard.workDaysEquivalent,
        verdict: keyboard.verdict,
        cooldownDays: keyboard.coolingOffDaysRecommended
    });

    if (keyboard.coolingOffDaysRecommended !== 2) {
        throw new Error(`Expected 2 days cooldown for 3.5k spend, got ${keyboard.coolingOffDaysRecommended}`);
    }
    console.log("✓ Test 1B (Moderate Impact) Passed!");

    // Case 3: Low-impact spend
    const book = await evaluateImpulseSpend("System Design Book", 800, "career", 65000);
    console.log("800 Book Result:", {
        item: book.itemName,
        cost: book.cost,
        hours: book.hoursOfLaborRequired,
        cooldownDays: book.coolingOffDaysRecommended
    });
    if (book.coolingOffDaysRecommended !== 1) {
        throw new Error(`Expected 1 day cooldown for 800 spend, got ${book.coolingOffDaysRecommended}`);
    }
    console.log("✓ Test 1C (Low Impact) Passed!");

    console.log("\n=================================================");
    console.log("TEST 2: LLM Tool Invocation with processChat");
    console.log("=================================================");

    const prompt = "Grace, I'm thinking of buying this ₹14,000 curved gaming monitor on Amazon. Is it worth it?";
    console.log(`Prompt: "${prompt}"`);

    const res = await processChat("test-spend-" + Date.now(), prompt);
    console.log("Tools invoked by Grace:", res.toolsUsed);
    console.log("\nGrace's Response:\n", res.text);

    if (!res.toolsUsed.includes("evaluateImpulseSpend")) {
        throw new Error("Grace failed to call evaluateImpulseSpend tool!");
    }

    console.log("\n✓ All Impulse Spend tests passed successfully!");
    process.exit(0);
}

runTests().catch(err => {
    console.error("Test failed:", err);
    process.exit(1);
});
