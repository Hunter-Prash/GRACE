import { useState, useRef, useEffect } from 'react';
import { Send, Mic, MicOff } from 'lucide-react';

const InputBox = ({ input, setInput, handleSend, stopSpeaking, isSpeaking }) => {
    const [isListening, setIsListening] = useState(false);
    const recognitionRef = useRef(null);
    const shouldListenRef = useRef(false);
    const baseTextRef = useRef('');

    // Cleanup on unmount
    useEffect(() => {
        return () => {
            shouldListenRef.current = false;
            if (recognitionRef.current) {
                try {
                    recognitionRef.current.abort();
                } catch {
                    /* ignore cleanup error */
                }
            }
        };
    }, []);

    const startRecognition = () => {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRecognition) {
            alert("Speech recognition is not supported in this browser. Please use Google Chrome or Microsoft Edge.");
            return;
        }

        try {
            const rec = new SpeechRecognition();
            // Continuous listening so it doesn't shut down after 1 second
            rec.continuous = true;
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
                    const text = event.results[i][0].transcript;
                    if (event.results[i].isFinal) {
                        finalTranscript += text + ' ';
                    } else {
                        interimTranscript += text;
                    }
                }

                const currentBase = baseTextRef.current ? baseTextRef.current.trim() + ' ' : '';
                const spoken = (finalTranscript + interimTranscript).trim();
                if (spoken) {
                    setInput(currentBase + spoken);
                }
            };

            rec.onerror = (event) => {
                console.warn("Speech recognition notice:", event.error);
                // Do NOT shut down on brief silence / no-speech!
                if (event.error === 'no-speech') {
                    return;
                }
                if (event.error === 'not-allowed') {
                    alert("Microphone permission was denied. Please allow microphone access in your browser address bar.");
                    shouldListenRef.current = false;
                    setIsListening(false);
                    return;
                }
            };

            rec.onend = () => {
                // If user hasn't explicitly stopped, keep listening alive (prevent 1s dropouts)
                if (shouldListenRef.current) {
                    try {
                        rec.start();
                    } catch {
                        setIsListening(false);
                        shouldListenRef.current = false;
                    }
                } else {
                    setIsListening(false);
                }
            };

            recognitionRef.current = rec;
            shouldListenRef.current = true;
            rec.start();
        } catch (err) {
            console.error("Speech recognition startup error:", err);
            shouldListenRef.current = false;
            setIsListening(false);
        }
    };

    const stopRecognition = () => {
        shouldListenRef.current = false;
        if (recognitionRef.current) {
            try {
                recognitionRef.current.stop();
            } catch {
                /* ignore stop error */
            }
        }
        setIsListening(false);
    };

    const toggleListen = () => {
        // Stop any active Grace voice response immediately
        if (stopSpeaking) {
            stopSpeaking();
        }

        if (isListening) {
            stopRecognition();
        } else {
            startRecognition();
        }
    };

    const handleTextChange = (e) => {
        // If Grace is speaking when user types, silence her immediately
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
                        if (isListening) {
                            stopRecognition();
                        }
                        handleSend(e);
                    }}
                    className={`flex items-end gap-1 sm:gap-2 bg-[#0a1114] border rounded-xl p-1.5 sm:p-2 shadow-[0_0_30px_rgba(0,0,0,0.5)] transition-all w-full ${
                        isListening 
                            ? 'border-red-500/80 shadow-[0_0_20px_rgba(239,68,68,0.3)]' 
                            : 'border-cyan-900/40 focus-within:border-cyan-500/60'
                    }`}
                >
                    <textarea
                        value={input}
                        onChange={handleTextChange}
                        placeholder={isListening ? "Listening continuously... Speak now" : "Type a message or tap the mic to speak..."}
                        className={`flex-1 max-h-32 min-h-[44px] bg-transparent resize-none outline-none p-3 text-cyan-50 transition-colors ${
                            isListening ? 'placeholder:text-red-400 font-medium' : 'placeholder:text-cyan-900/60'
                        }`}
                        rows={1}
                        onKeyDown={(e) => {
                            if (e.key === 'Enter' && !e.shiftKey) {
                                e.preventDefault();
                                if (isListening) {
                                    stopRecognition();
                                }
                                handleSend(e);
                            }
                        }}
                    />

                    {/* Microphone Button */}
                    <button
                        type="button"
                        onClick={toggleListen}
                        title={isListening ? "Stop listening" : "Start speaking"}
                        className={`p-3 mb-0.5 rounded-lg border transition-all cursor-pointer ${
                            isListening 
                                ? 'bg-red-500/25 text-red-400 border-red-500/80 hover:bg-red-500/35 shadow-[0_0_15px_rgba(239,68,68,0.5)] animate-pulse' 
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
                    <span className={isListening ? "text-red-400 font-bold" : ""}>
                        {isListening ? "● LISTENING (TAP MIC TO FINISH)" : "GRACE LIFE OS // INTERFACE"}
                    </span>
                    <span>ENTER TO SEND</span>
                </div>
            </div>
        </footer>
    );
};

export default InputBox;
