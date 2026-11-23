import dotenv from 'dotenv';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
dotenv.config({ path: path.resolve(__dirname, '../.env') });

import { processChat } from '../api-worker/src/services/llm.service.js';

async function test() {
    console.log("Testing processChat with brain dump prompt...");
    const prompt = process.argv[2] || "Grace, remember that I left my car keys on the kitchen counter";
    console.log(`Prompt: "${prompt}"`);
    const res = await processChat("test-session-" + Date.now(), prompt);
    console.log("\n========================================================");
    console.log("Tools used:", res.toolsUsed);
    console.log("Response text:", res.text);
    console.log("========================================================\n");
    process.exit(0);
}

test().catch(err => {
    console.error("Test failed:", err);
    process.exit(1);
});
