import dotenv from 'dotenv';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
dotenv.config({ path: path.resolve(__dirname, '../.env') });

import { searchYouTube } from '../api-worker/src/services/media.service.js';
import { processChat } from '../api-worker/src/services/llm.service.js';

async function runTests() {
    console.log("=================================================");
    console.log("TEST 1: Direct YouTube Search Resolution");
    console.log("=================================================");

    const starboy = await searchYouTube("Starboy The Weeknd");
    console.log("Search Result:", starboy);

    if (!starboy || !starboy.videoId || !starboy.url.includes("autoplay=1")) {
        throw new Error("Failed to resolve Starboy with autoplay URL!");
    }
    console.log("✓ Test 1 Passed: Successfully resolved Starboy to video ID:", starboy.videoId);

    console.log("\n=================================================");
    console.log("TEST 2: LLM Tool Invocation ('play Starboy')");
    console.log("=================================================");

    const prompt = "Grace, open YouTube and play Starboy.";
    console.log(`Prompt: "${prompt}"`);

    const res = await processChat("test-media-" + Date.now(), prompt);
    console.log("Tools invoked by Grace:", res.toolsUsed);
    console.log("Client Commands returned:", res.clientCommands);
    console.log("Grace's Response text:\n", res.text);

    if (!res.toolsUsed.includes("playMedia") && !res.toolsUsed.includes("openResource")) {
        throw new Error("Grace failed to call playMedia or openResource!");
    }

    const playCmd = res.clientCommands.find(c => c.type === 'openResource');
    if (!playCmd || !playCmd.resourceName.includes("watch?v=")) {
        throw new Error("clientCommands missing direct YouTube watch URL!");
    }

    console.log("\n✓ All Media Playback tests passed successfully!");
    process.exit(0);
}

runTests().catch(err => {
    console.error("Test execution failed:", err);
    process.exit(1);
});
