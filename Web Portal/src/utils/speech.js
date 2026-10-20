/**
 * Clean text for natural speech synthesis by removing Markdown, URLs, code blocks, and symbols.
 */
export function cleanSpeechText(text) {
    if (!text) return "";
    return text
        // Remove code blocks
        .replace(/```[\s\S]*?```/g, "Code block omitted.")
        .replace(/`([^`]+)`/g, "$1")
        // Remove markdown formatting
        .replace(/\*\*([^*]+)\*\*/g, "$1")
        .replace(/\*([^*]+)\*/g, "$1")
        .replace(/__([^_]+)__/g, "$1")
        .replace(/_([^_]+)_/g, "$1")
        .replace(/#{1,6}\s+/g, "")
        // Remove markdown links [title](url) -> title
        .replace(/\[([^\]]+)\]\([^)]+\)/g, "$1")
        // Remove raw URLs
        .replace(/https?:\/\/\S+/g, "")
        // Remove bullet points and number lists
        .replace(/^\s*[-*+]\s+/gm, "")
        .replace(/^\s*\d+\.\s+/gm, "")
        // Remove emojis and miscellaneous symbols
        .replace(/[\u{1F300}-\u{1F9FF}\u{2600}-\u{26FF}\u{2700}-\u{27BF}]/gu, "")
        // Clean multiple newlines and spaces
        .replace(/\n+/g, " ")
        .replace(/\s+/g, " ")
        .trim();
}

/**
 * Prioritizes high-quality natural female voices across browsers (Edge, Chrome, Safari, etc.)
 */
export function selectGraceVoice(voices) {
    if (!voices || voices.length === 0) return null;

    // Tier 1: Microsoft Natural Online Voices (Edge / Windows)
    const naturalFemale = voices.find(v => 
        v.name.includes("Natural") && (v.name.includes("Jenny") || v.name.includes("Aria") || v.name.includes("Sonia") || v.name.includes("Female"))
    );
    if (naturalFemale) return naturalFemale;

    // Tier 2: Google Premium Voices (Chrome / Android)
    const googleFemale = voices.find(v => 
        v.name.includes("Google") && (v.name.includes("UK English Female") || v.name.includes("US English") || v.name.toLowerCase().includes("female"))
    );
    if (googleFemale) return googleFemale;

    // Tier 3: Apple / Safari Voices (Samantha, Victoria, Karen, Moira)
    const appleFemale = voices.find(v => 
        v.name.includes("Samantha") || v.name.includes("Victoria") || v.name.includes("Karen") || v.name.includes("Moira")
    );
    if (appleFemale) return appleFemale;

    // Tier 4: Any English female voice
    const anyFemale = voices.find(v => 
        v.lang.startsWith("en") && (v.name.toLowerCase().includes("female") || v.name.toLowerCase().includes("woman") || v.name.includes("Zira"))
    );
    if (anyFemale) return anyFemale;

    // Tier 5: Standard English voice fallback
    const anyEnglish = voices.find(v => v.lang === "en-US" || v.lang === "en-GB" || v.lang.startsWith("en"));
    return anyEnglish || voices[0];
}

