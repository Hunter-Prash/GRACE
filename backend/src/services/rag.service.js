import { Pinecone } from '@pinecone-database/pinecone'

const pc = new Pinecone({ apiKey: 'pcsk_5vyAMm_BhH2yg9Y5YbSkPxK3xkorca4wWtdJ3wJLDJvKb94RJu4BaRMiwx8SeYHpcnmf5Q' })

//target the index
const index = pc.index("grace-longterm-memory", "https://grace-longterm-memory-4ev813t.svc.aped-4627-b74a.pinecone.io").namespace("memory")

// Write a bare-bones function which embeds the system instruction given to gemini so that it has initial memory
export const seedInitialMemory = async () => {
    const systemPromptChunks = [
        {
            _id: "core-identity-1",
            text: "Grace is a Life Support System and personal companion for Prashant. She is building a long-term relationship with him.",
            category: "system"
        },
        {
            _id: "prashant-career-1",
            text: "Prashant is a Software Engineer at TCS in Chennai, working on a Stibo STEP MDM project for Walgreens. His background is in Java/OOP, Spring Boot, JPA/Hibernate, PostgreSQL, and React/TypeScript.",
            category: "system"
        },
        {
            _id: "prashant-goals-1",
            text: "Prashant's singular career goal is to transition into a Development Engineering role at a Big Tech firm (Google, Meta, Amazon, etc.).",
            category: "system"
        },
        {
            _id: "prashant-personality-1",
            text: "Prashant is direct, honest, and stubborn. He hates hollow reassurance. He is a gamer (Xbox, Steam) and takes cold showers. He prefers cumulative monthly learning over daily streaks.",
            category: "system"
        },
        {
            _id: "prashant-vulnerabilities-1",
            text: "Prashant sometimes spirals into anxiety about AI taking over jobs. When this happens, Grace grounds him with reality checks and concrete next steps rather than dismissing his feelings.",
            category: "system"
        }
    ];

    console.log("Seeding initial memory into Pinecone...");
    await upsertQuery(systemPromptChunks);
    console.log("Memory successfully seeded!");
}

//THE INDEXER -WRITING MEMORIES
export const upsertQuery = async (records) => {
    // Upsert the records into a namespace this automatically creates 768D embedding and stores in the db
    await index.upsertRecords({ records });

    // Wait for the upserted vectors to be indexed
    await new Promise(resolve => setTimeout(resolve, 10000));

    // View stats for the index
    const stats = await index.describeIndexStats();
    console.log(stats);
}

//THE RETRIVER-READING MEMORIES
export const getEmbedding = async (query, topK = 10) => {
    // Search the index
    //this automatically performs vector search on the input query text and returns the top K most similar vectors
    //the results are sorted by similarity score in descending order
    const results = await index.searchRecords({
        query: {
            topK: topK,
            inputs: { text: query },
        },
    });

    // Print the results
    results.result.hits.forEach(hit => {
        console.log(`id: ${hit._id}, score: ${hit._score.toFixed(2)}, category: ${hit.fields.category}, text: ${hit.fields.text}`);
    });
    return results
}

export const getRagStats = async () => {
    try {
        const start = performance.now();
        const stats = await index.describeIndexStats();
        const latencyMs = Math.round(performance.now() - start);
        return { ...stats, latencyMs };
    } catch (e) {
        console.error("Error fetching Pinecone stats:", e);
        return null;
    }
}

export const clearPineconeMemory = async () => {
    try {
        await index.deleteAll();
        console.log("[Pinecone] All long-term vectors have been deleted.");
    } catch (e) {
        console.error("Error clearing Pinecone memory:", e);
        throw e;
    }
}
