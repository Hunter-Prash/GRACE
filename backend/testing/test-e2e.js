async function runEndToEndTest() {
    console.log("🚀 Starting E2E Hybrid Cloud Test...");
    console.log("Sending manual trigger command to local API to fire EventBridge...\n");

    try {
        const response = await fetch('http://localhost:3000/api/trigger-indexer');
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        console.log("✅ Local API responded successfully!");
        console.log("Response:", data);
        console.log("\nIf the pipeline is working:");
        console.log("1. The local API just fired an event to 'grace-ai-bus' in AWS.");
        console.log("2. EventBridge routed it to the 'GraceIndexerWorker' Lambda.");
        console.log("3. You should see a new Discord Log in a few seconds from the Cloud!");
        
    } catch (error) {
        console.error("❌ Test Failed!");
        if (error.cause && error.cause.code === 'ECONNREFUSED') {
            console.error("Make sure you are running 'node local-server.js' inside the api-worker directory!");
        } else {
            console.error(error.message);
        }
    }
}

runEndToEndTest();
