import { useState, useRef, useEffect, useCallback } from 'react';
import { motion } from 'framer-motion';
import axios from 'axios';
import Chatlog from './Components/Chatlog';
import InputBox from './Components/InputBox';
import HeaderOrb from './Components/HeaderOrb';
import { speakGrace, stopGraceSpeech } from './utils/speech';

const API_BASE_URL = "https://y32tddvhc0.execute-api.ap-south-1.amazonaws.com/Prod";

// Pre-signed fallback token to ensure requests to AWS Lambda succeed without any login gate
const DEFAULT_AUTH_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJlbWFpbCI6InJhamFqaS5wcmFzaGFudEBnbWFpbC5jb20iLCJpYXQiOjE3OTI1MzA4OTEsImV4cCI6MjEwNzg5MDg5MX0.JOatvKWmfULlPiHiZ6dOAWPbJQHrHvSzmBZjI4DOSiI";

export default function App() {
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const [isSpeaking, setIsSpeaking] = useState(false);
    const [speakingText, setSpeakingText] = useState(null);
    const bottomRef = useRef(null);

    // Get active authorization token (stored or default)
    const token = localStorage.getItem('grace_token') || DEFAULT_AUTH_TOKEN;

    // Pre-warm browser speech synthesis voices
    useEffect(() => {
        if ('speechSynthesis' in window) {
            window.speechSynthesis.getVoices();
            window.speechSynthesis.onvoiceschanged = () => {
                window.speechSynthesis.getVoices();
            };
        }
        return () => {
            stopGraceSpeech();
        };
    }, []);

    // Stop speaking immediately
    const stopSpeaking = useCallback(() => {
        stopGraceSpeech();
        setIsSpeaking(false);
        setSpeakingText(null);
    }, []);

    // Play/Stop a specific message
    const handleSpeakMessage = useCallback((text) => {
        if (speakingText === text) {
            stopSpeaking();
            return;
        }

        stopSpeaking();
        setSpeakingText(text);
        speakGrace(
            text,
            () => setIsSpeaking(true),
            () => {
                setIsSpeaking(false);
                setSpeakingText(null);
            }
        );
    }, [speakingText, stopSpeaking]);

    // Fetch initial chat history
    useEffect(() => {
        const fetchChat = async () => {
            try {
                const response = await axios.get(`${API_BASE_URL}/api/history/default`, {
                    headers: { Authorization: `Bearer ${token}` }
                });
                if (response.data && Array.isArray(response.data.history)) {
                    const now = Date.now();
                    const history = response.data.history.map((item, idx) => ({
                        ...item,
                        time: item.time || new Date(now - (response.data.history.length - 1 - idx) * 60000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
                    }));
                    setMessages(history);
                }
            } catch (e) {
                console.warn("Could not load initial chat history:", e.message);
            }
        };
        fetchChat();
    }, [token]);

    // Auto-scroll chat to latest message
    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages, loading]);

    // Handle sending a message
    const handleSend = async (e) => {
        if (e) e.preventDefault();
        const textToSend = input.trim();
        if (!textToSend) return;

        const currentTime = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

        // 1. Immediately cut off any voice playback
        stopSpeaking();

        // 2. CRITICAL FIX: Clear input immediately so user can type next message without it getting wiped
        setInput("");

        // 3. Optimistically render user message
        setMessages((prev) => [...prev, {
            role: 'user',
            parts: [{ text: textToSend }],
            time: currentTime
        }]);

        setLoading(true);

        try {
            const response = await axios.post(
                `${API_BASE_URL}/api/chat`,
                { text: textToSend },
                { headers: { Authorization: `Bearer ${token}` } }
            );

            const aiText = response.data?.text || "No response received.";
            const responseTime = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
            setMessages((prev) => [...prev, {
                role: 'model',
                parts: [{ text: aiText }],
                time: responseTime
            }]);

            // Automatically speak response at fast, crisp speed
            handleSpeakMessage(aiText);

        } catch (error) {
            console.error("Chat error:", error);
            const errorMsg = error.response?.data?.details || error.response?.data?.error || "I ran into a connection issue. Please try again.";
            const errTime = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
            setMessages((prev) => [...prev, {
                role: 'model',
                parts: [{ text: typeof errorMsg === 'string' ? errorMsg : "Connection error. Please try again." }],
                time: errTime
            }]);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="relative flex flex-col h-[100dvh] bg-[#020404] text-cyan-50 font-sans selection:bg-cyan-900 selection:text-cyan-50 overflow-hidden">
            {/* Animated Cyber Grid Background */}
            <div className="absolute inset-0 cyber-grid animate-grid pointer-events-none z-0"></div>

            <HeaderOrb 
                isSpeaking={isSpeaking}
                stopSpeaking={stopSpeaking}
            />

            <Chatlog 
                messages={messages} 
                bottomRef={bottomRef}
                onSpeakMessage={handleSpeakMessage}
                speakingText={speakingText}
            />

            {loading && (
                <div className="flex justify-center items-center py-2 z-10 shrink-0">
                    <motion.div
                        className="flex items-center gap-3 px-5 py-2 rounded-full border border-cyan-500/50 bg-cyan-950/40 shadow-[0_0_15px_rgba(34,211,238,0.2)] backdrop-blur-md"
                        animate={{ opacity: [0.6, 1, 0.6] }}
                        transition={{ duration: 1.5, repeat: Infinity, ease: "easeInOut" }}
                    >
                        <span className="text-[10px] tracking-widest text-cyan-400 font-bold uppercase drop-shadow-[0_0_5px_rgba(34,211,238,0.8)]">
                            GRACE IS PROCESSING
                        </span>
                        <div className="flex gap-1 mt-0.5">
                            <motion.div className="w-1.5 h-1.5 bg-cyan-400 rounded-full shadow-[0_0_5px_rgba(34,211,238,0.8)]" animate={{ y: [0, -4, 0] }} transition={{ duration: 0.6, repeat: Infinity, delay: 0 }} />
                            <motion.div className="w-1.5 h-1.5 bg-cyan-400 rounded-full shadow-[0_0_5px_rgba(34,211,238,0.8)]" animate={{ y: [0, -4, 0] }} transition={{ duration: 0.6, repeat: Infinity, delay: 0.2 }} />
                            <motion.div className="w-1.5 h-1.5 bg-cyan-400 rounded-full shadow-[0_0_5px_rgba(34,211,238,0.8)]" animate={{ y: [0, -4, 0] }} transition={{ duration: 0.6, repeat: Infinity, delay: 0.4 }} />
                        </div>
                    </motion.div>
                </div>
            )}

            <InputBox
                input={input}
                setInput={setInput}
                handleSend={handleSend}
                stopSpeaking={stopSpeaking}
                isSpeaking={isSpeaking}
            />
        </div>
    );
}
