import React, { useState, useEffect } from 'react'
import { Send, Mic, MicOff } from 'lucide-react'

const InputBox = ({ input, setInput, handleSend }) => {
    const [isListening, setIsListening] = useState(false);
    const [recognition, setRecognition] = useState(null);

    useEffect(() => {
        if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            const rec = new SpeechRecognition();
            rec.continuous = false;
            rec.interimResults = false;
            
            rec.onresult = (event) => {
                const transcript = event.results[0][0].transcript;
                setInput(prev => prev + (prev ? ' ' : '') + transcript);
            };

            rec.onerror = (event) => {
                console.error("Speech recognition error", event.error);
                setIsListening(false);
            };

            rec.onend = () => {
                setIsListening(false);
            };

            setRecognition(rec);
        }
    }, [setInput]);

    const toggleListen = () => {
        if (!recognition) {
            alert("Your browser does not support Speech Recognition.");
            return;
        }

        if (isListening) {
            recognition.stop();
        } else {
            recognition.start();
            setIsListening(true);
        }
    };

    return (
        <footer className="p-2 sm:p-4 bg-gradient-to-t from-[#020404] to-transparent shrink-0 z-10">
            <div className="max-w-3xl mx-auto w-full">
                <form
                    onSubmit={handleSend}
                    className="flex items-end gap-1 sm:gap-2 bg-[#0a1114] border border-cyan-900/40 rounded-xl p-1.5 sm:p-2 shadow-[0_0_30px_rgba(0,0,0,0.5)] focus-within:border-cyan-500/50 transition-colors w-full"
                >
                    {/* The text area where you will dictate using mobile keyboard */}
                    <textarea
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        placeholder="Dictate message..."
                        className="flex-1 max-h-32 min-h-[44px] bg-transparent resize-none outline-none p-3 text-cyan-50 placeholder:text-cyan-900/60"
                        rows={1}
                        onKeyDown={(e) => {
                            if (e.key === 'Enter' && !e.shiftKey) {
                                e.preventDefault();
                                handleSend(e);
                            }
                        }}
                    />

                    <button
                        type="button"
                        onClick={toggleListen}
                        className={`p-3 mb-0.5 rounded-lg border transition-all ${
                            isListening 
                                ? 'bg-red-500/20 text-red-400 border-red-500/50 hover:bg-red-500/30 shadow-[0_0_15px_rgba(239,68,68,0.3)] animate-pulse' 
                                : 'bg-cyan-950/50 text-cyan-500 border-cyan-900/50 hover:bg-cyan-900/50 hover:text-cyan-400'
                        }`}
                    >
                        {isListening ? <MicOff size={20} /> : <Mic size={20} />}
                    </button>

                    <button
                        type="submit"
                        disabled={!input.trim()}
                        className="p-3 mb-0.5 rounded-lg bg-cyan-950/50 text-cyan-500 border border-cyan-900/50 hover:bg-cyan-900/50 hover:text-cyan-400 disabled:opacity-30 disabled:hover:bg-transparent transition-all"
                    >
                        <Send size={20} />
                    </button>
                </form>
                <div className="text-center mt-3">
                    <span className="text-[10px] tracking-widest text-slate-600">GRACE WEB INTERFACE // PROTOTYPE</span>
                </div>
            </div>
        </footer>
    )
}

export default InputBox
