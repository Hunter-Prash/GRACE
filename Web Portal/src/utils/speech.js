/**
 * Clean text for natural speech synthesis by removing Markdown, URLs, code blocks, and symbols.
 */
export function cleanSpeechText(text) {
    if (!text) return "";
    return text
        // Remove code blocks
        .replace(/```[\s\S]*?```/g, "Code block omitted.")
        .replace(/`([^`]+)`/g, "$1")
        // Remove bold, italic, headers
        .replace(/\*\*([^*]+)\*\*/g, "$1")
        .replace(/\*([^*]+)\*/g, "$1")
        .replace(/__([^_]+)__/g, "$1")
        .replace(/_([^_]+)_/g, "$1")
        .replace(/#{1,6}\s+/g, "")
        // Remove markdown links [title](url) -> title
        .replace(/\[([^\]]+)\]\([^)]+\)/g, "$1")
        // Remove raw URLs
        .replace(/https?:\/\/\S+/g, "")
        // Remove bullet markers and list numbers
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
 * Select the best quality natural English female voice available in the browser.
 */
export function selectGraceVoice(voices) {
    if (!voices || voices.length === 0) return null;

    // Tier 1: Microsoft Natural Online Voices (Edge / Windows: Jenny, Aria, Sonia)
    const naturalFemale = voices.find(v => 
        v.name.includes("Natural") && (v.name.includes("Jenny") || v.name.includes("Aria") || v.name.includes("Sonia") || v.name.includes("Female"))
    );
    if (naturalFemale) return naturalFemale;

    // Tier 2: Google Premium Voices (Google UK English Female sounds far better than US)
    const googleUkFemale = voices.find(v => v.name.includes("Google") && v.name.includes("UK English Female"));
    if (googleUkFemale) return googleUkFemale;

    const googleFemale = voices.find(v => v.name.includes("Google") && (v.name.includes("Female") || v.name.includes("US English")));
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

// Global reference to prevent Chrome garbage-collecting the utterance mid-speech
let currentUtterance = null;

/**
 * Plays speech cleanly with fast natural pacing and Chrome GC protection.
 */
export function speakGrace(text, onStart, onEnd) {
    if (!('speechSynthesis' in window)) return;

    const cleaned = cleanSpeechText(text);
    if (!cleaned) return;

    // Cancel any current speech
    window.speechSynthesis.cancel();

    const utterance = new SpeechSynthesisUtterance(cleaned);
    currentUtterance = utterance; // Keep alive in memory

    const voices = window.speechSynthesis.getVoices();
    const voice = selectGraceVoice(voices);
    if (voice) {
        utterance.voice = voice;
    }

    // Snappy, energetic conversational speed (no dragging slowness)
    utterance.rate = 1.25;
    utterance.pitch = 1.0;

    utterance.onstart = () => {
        if (onStart) onStart();
    };

    utterance.onend = () => {
        currentUtterance = null;
        if (onEnd) onEnd();
    };

    utterance.onerror = () => {
        currentUtterance = null;
        if (onEnd) onEnd();
    };

    // Chrome resume fix
    if (window.speechSynthesis.paused) {
        window.speechSynthesis.resume();
    }

    // Slight delay to avoid browser audio lock
    setTimeout(() => {
        window.speechSynthesis.speak(utterance);
    }, 25);
}

export function stopGraceSpeech() {
    if ('speechSynthesis' in window) {
        window.speechSynthesis.cancel();
    }
    if (currentUtterance) {
        currentUtterance = null;
    }
}
