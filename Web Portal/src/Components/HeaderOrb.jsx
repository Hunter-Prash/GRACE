import React from 'react';
import { motion } from 'framer-motion';
import { Volume2, VolumeX, Square } from 'lucide-react';

const HeaderOrb = ({ isSpeaking = false, stopSpeaking, voiceEnabled = true, setVoiceEnabled }) => {
    return (
        <header className="flex flex-col items-center justify-center p-3 sm:p-5 pb-8 sm:pb-10 bg-gradient-to-b from-[#020404] via-[#020404]/90 to-transparent shrink-0 z-20 relative">
            {/* Top Bar with Audio Controls */}
            <div className="w-full max-w-3xl flex justify-between items-center mb-2 px-2">
                <div className="flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse shadow-[0_0_8px_rgba(52,211,153,0.8)]" />
                    <span className="text-[10px] tracking-widest text-emerald-400/80 font-mono font-bold">ONLINE</span>
                </div>

                <div className="flex items-center gap-2">
                    {/* Active Speaking Indicator + Stop button */}
                    {isSpeaking && (
                        <button
                            onClick={stopSpeaking}
                            title="Stop speaking"
                            className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-cyan-950/80 border border-cyan-400/60 text-cyan-300 text-[11px] font-mono shadow-[0_0_12px_rgba(34,211,238,0.4)] hover:bg-cyan-900/60 transition-all cursor-pointer animate-pulse"
                        >
                            <Square size={10} className="fill-cyan-400" />
                            <span>MUTE AUDIO</span>
                        </button>
                    )}

                    {/* Voice Toggle Button */}
                    <button
                        onClick={() => {
                            if (voiceEnabled && stopSpeaking) stopSpeaking();
                            if (setVoiceEnabled) setVoiceEnabled(!voiceEnabled);
                        }}
                        title={voiceEnabled ? "Mute voice responses" : "Enable voice responses"}
                        className={`p-1.5 rounded-lg border text-xs transition-all cursor-pointer ${
                            voiceEnabled 
                                ? 'bg-cyan-950/40 border-cyan-900/60 text-cyan-400 hover:border-cyan-500/60 shadow-[0_0_10px_rgba(34,211,238,0.15)]' 
                                : 'bg-red-950/40 border-red-900/60 text-red-400 hover:border-red-500/60'
                        }`}
                    >
                        {voiceEnabled ? <Volume2 size={16} /> : <VolumeX size={16} />}
                    </button>
                </div>
            </div>

            {/* The Orb Container */}
            <div className="relative flex items-center justify-center w-14 h-14 sm:w-16 sm:h-16">
                {/* Expanding Sonar Rings */}
                <motion.div
                    className={`absolute inset-0 rounded-full border ${isSpeaking ? 'border-cyan-400/60' : 'border-cyan-500/30'}`}
                    animate={{ scale: isSpeaking ? [1, 2.8] : [1, 2.3], opacity: [0.8, 0] }}
                    transition={{ duration: isSpeaking ? 1.5 : 3, repeat: Infinity, ease: "easeOut", delay: 0 }}
                />
                
                <motion.div
                    className={`absolute inset-0 rounded-full border ${isSpeaking ? 'border-cyan-300/40' : 'border-cyan-400/20'}`}
                    animate={{ scale: isSpeaking ? [1, 2.8] : [1, 2.3], opacity: [0.8, 0] }}
                    transition={{ duration: isSpeaking ? 1.5 : 3, repeat: Infinity, ease: "easeOut", delay: isSpeaking ? 0.5 : 1 }}
                />

                <motion.div
                    className={`absolute inset-0 rounded-full border ${isSpeaking ? 'border-cyan-500/30' : 'border-cyan-600/20'}`}
                    animate={{ scale: isSpeaking ? [1, 2.8] : [1, 2.3], opacity: [0.8, 0] }}
                    transition={{ duration: isSpeaking ? 1.5 : 3, repeat: Infinity, ease: "easeOut", delay: isSpeaking ? 1.0 : 2 }}
                />

                {/* Solid Core Orb */}
                <motion.div
                    animate={{ 
                        scale: isSpeaking ? [1, 1.25, 1] : [1, 1.08, 1], 
                        opacity: [0.85, 1, 0.85] 
                    }}
                    transition={{ duration: isSpeaking ? 0.8 : 2, repeat: Infinity, ease: "easeInOut" }}
                    className="relative w-8 h-8 sm:w-9 sm:h-9 rounded-full border-2 border-cyan-400 shadow-[0_0_20px_rgba(0,212,255,0.7)] bg-cyan-950 flex items-center justify-center cursor-pointer"
                    onClick={() => {
                        if (isSpeaking && stopSpeaking) stopSpeaking();
                    }}
                    title={isSpeaking ? "Click orb to stop speech" : "Grace"}
                >
                    <div className="w-full h-full rounded-full bg-cyan-400/30 blur-[2px]" />
                </motion.div>
            </div>

            <h1 className="mt-1 text-[10px] sm:text-xs tracking-[0.3em] text-cyan-400/80 font-bold uppercase drop-shadow-[0_0_5px_rgba(0,212,255,0.3)]">
                GRACE LIFE OS
            </h1>
        </header>
    );
};

export default HeaderOrb;
