import ytSearch from 'yt-search';

/**
 * Searches YouTube for a track, video, or playlist query.
 * Returns direct videoId and watch URL with autoplay.
 */
export async function searchYouTube(query) {
    if (!query || typeof query !== 'string') {
        throw new Error("A valid search query is required.");
    }

    try {
        console.log(`[Media] Searching YouTube for: "${query}"`);
        const searchResults = await ytSearch(query);

        if (!searchResults || !searchResults.videos || searchResults.videos.length === 0) {
            console.warn(`[Media] No YouTube videos found for: "${query}"`);
            return null;
        }

        const topVideo = searchResults.videos[0];
        const watchUrl = `https://www.youtube.com/watch?v=${topVideo.videoId}&autoplay=1`;

        return {
            title: topVideo.title,
            videoId: topVideo.videoId,
            url: watchUrl,
            duration: topVideo.timestamp,
            author: topVideo.author?.name || "Unknown",
            thumbnail: topVideo.thumbnail
        };
    } catch (e) {
        console.error(`[Media] YouTube search failed for "${query}":`, e.message);
        return null;
    }
}
