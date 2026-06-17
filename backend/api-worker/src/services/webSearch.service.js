const TAVILY_API_KEY = "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";

export async function searchWeb(query) {
    try {
        console.log(`[WEB SEARCH] Using Tavily for: "${query}"`);
        
        const response = await fetch("https://api.tavily.com/search", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                api_key: TAVILY_API_KEY,
                query: query,
                search_depth: "basic",
                include_answer: false,
                include_images: false,
                include_raw_content: false,
                max_results: 5
            })
        });

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`Tavily API error (${response.status}): ${errorText}`);
        }

        const searchResults = await response.json();

        if (!searchResults.results || searchResults.results.length === 0) {
            return "No results found for this query.";
        }

        // Format them cleanly for the LLM to read
        let formattedResults = `Search Results for "${query}":\n\n`;
        
        for (let i = 0; i < searchResults.results.length; i++) {
            const res = searchResults.results[i];
            formattedResults += `[Result ${i + 1}]\n`;
            formattedResults += `Title: ${res.title}\n`;
            formattedResults += `Snippet: ${res.content}\n`;
            formattedResults += `URL: ${res.url}\n\n`;
        }

        console.log(`[WEB SEARCH] Found ${searchResults.results.length} highly relevant snippets from Tavily.`);
        return formattedResults;

    } catch (error) {
        console.error("[WEB SEARCH ERROR]", error);
        return `Search failed: ${error.message}`;
    }
}
