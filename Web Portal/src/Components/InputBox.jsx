import React, { useState, useRef, useEffect } from 'react';
import { Send, Mic, MicOff } from 'lucide-react';

const InputBox = ({ input, setInput, handleSend, stopSpeaking, isSpeaking }) => {
    const [isListening, setIsListening] = useState(false);
    const recognitionRef = useRef(null);
    const baseTextRef = useRef('');

    // Cleanup speech recognition on unmount
    useEffect(() => {
        return () => {
            if (recognitionRef.current) {
                try {
                    recognitionRef.current.abort();
                } catch (e) {
                    // Ignore abort errors on unmount
                }
            }
        };
    }, []);

    const toggleListen = () => {
        // If Grace is currently speaking, shut her up immediately
        if (stopSpeaking) {
            stopSpeaking();
        }

        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRecognition) {
            alert("Speech recognition is not supported in this browser. Please use Google Chrome or Microsoft Edge.");
            return;
        }

        if (isListening) {
            if (recognitionRef.current) {
                try {
                    recognitionRef.current.stop();
                } catch (e) {
                    // Ignore
                }
            }
            setIsListening(false);
            return;
        }

        try {
            const rec = new SpeechRecognition();
            rec.continuous = false;
            rec.interimResults = true;
            rec.lang = 'en-US';

            baseTextRef.current = input;

            rec.onstart = () => {
                setIsListening(true);
            };

            rec.onresult = (event) => {
                let interimTranscript = '';
                let finalTranscript = '';

                for (let i = event.resultIndex; i < event.results.length; ++i) {
                    if (event.results[i].isFinal) {
                        finalTranscript += event.results[i][0].transcript;
                    } else {
                        interimTranscript += event.results[i][0].transcript;
                    }
                }

                const currentBase = baseTextRef.current ? baseTextRef.current.trim() + ' ' : '';
                const spoken = finalTranscript || interimTranscript;
                setInput(currentBase + spoken);
            };

            rec.onerror = (event) => {
                console.warn("Speech recognition error:", event.error);
                if (event.error === 'not-allowed') {
                    alert("Microphone access was denied. Please allow microphone permissions in your browser.");
                }
                setIsListening(false);
            };

            rec.onend = () => {
                setIsListening(false);
            };

            recognitionRef.current = rec;
            rec.start();
        } catch (err) {
            console.error("Failed to start speech recognition:", err);
            setIsListening(false);
        }
    };

    const handleTextChange = (e) => {
        // If user starts typing while Grace is speaking, cut off Grace's voice immediately
        if (isSpeaking && stopSpeaking) {
            stopSpeaking();
        }
        setInput(e.target.value);
    };

    return (
        <footer className="p-2 sm:p-4 bg-gradient-to-t from-[#020404] via-[#020404]/90 to-transparent shrink-0 z-20">
            <div className="max-w-3xl mx-auto w-full">
                <form
                    onSubmit={(e) => {
                        e.preventDefault();
                        if (isListening && recognitionRef.current) {
                            try { recognitionRef.current.stop(); } catch (err) {}
                            setIsListening(false);
                        }
                        handleSend(e);
                    }}
                    className={`flex items-end gap-1 sm:gap-2 bg-[#0a1114] border rounded-xl p-1.5 sm:p-2 shadow-[0_0_30px_rgba(0,0,0,0.5)] transition-all w-full ${
                        isListening 
                            ? 'border-red-500/70 shadow-[0_0_20px_rgba(239,68,68,0.25)]' 
                            : 'border-cyan-900/40 focus-within:border-cyan-500/60'
                    }`}
                >
                    <textarea
                        value={input}
                        onChange={handleTextChange}
                        placeholder={isListening ? "Listening... Speak to Grace" : "Type a message or tap the mic to speak..."}
                        className={`flex-1 max-h-32 min-h-[44px] bg-transparent resize-none outline-none p-3 text-cyan-50 transition-colors ${
                            isListening ? 'placeholder:text-red-400/80 animate-pulse' : 'placeholder:text-cyan-900/60'
                        }`}
                        rows={1}
                        onKeyDown={(e) => {
                            if (e.key === 'Enter' && !e.shiftKey) {
                                e.preventDefault();
                                if (isListening && recognitionRef.current) {
                                    try { recognitionRef.current.stop(); } catch (err) {}
                                    setIsListening(false);
                                }
                                handleSend(e);
                            }
                        }}
                    />

                    {/* Microphone Button */}
                    <button
                        type="button"
                        onClick={toggleListen}
                        title={isListening ? "Stop listening" : "Speak to Grace"}
                        className={`p-3 mb-0.5 rounded-lg border transition-all cursor-pointer ${
                            isListening 
                                ? 'bg-red-500/20 text-red-400 border-red-500/60 hover:bg-red-500/30 shadow-[0_0_15px_rgba(239,68,68,0.4)] animate-pulse' 
                                : 'bg-cyan-950/50 text-cyan-400 border-cyan-900/50 hover:bg-cyan-900/50 hover:text-cyan-300'
                        }`}
                    >
                        {isListening ? <MicOff size={20} /> : <Mic size={20} />}
                    </button>

                    {/* Send Button */}
                    <button
                        type="submit"
                        disabled={!input.trim()}
                        title="Send message"
                        className="p-3 mb-0.5 rounded-lg bg-cyan-950/50 text-cyan-400 border border-cyan-900/50 hover:bg-cyan-900/50 hover:text-cyan-300 disabled:opacity-30 disabled:hover:bg-transparent transition-all cursor-pointer disabled:cursor-not-allowed"
                    >
                        <Send size={20} />
                    </button>
                </form>

                <div className="flex items-center justify-between mt-2 px-1 text-[10px] tracking-widest text-slate-500">
                    <span>{isListening ? "● LISTENING..." : "GRACE LIFE OS // INTERFACE"}</span>
                    <span>ENTER TO SEND / SHIFT+ENTER NEW LINE</span>
                </div>
            </div>
        </footer>
    );
};

export default InputBox;
