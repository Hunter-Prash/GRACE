import { motion } from 'framer-motion';

const HeaderOrb = ({ isSpeaking = false, stopSpeaking }) => {
    return (
        <header className="flex flex-col items-center justify-center p-3 sm:p-5 pb-6 sm:pb-8 bg-gradient-to-b from-[#020404] via-[#020404]/90 to-transparent shrink-0 z-20 relative">
            {/* Top Online Indicator */}
            <div className="w-full max-w-3xl flex justify-between items-center mb-1 px-4">
                <div className="flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse shadow-[0_0_8px_rgba(52,211,153,0.8)]" />
                    <span className="text-[10px] tracking-widest text-emerald-400/80 font-mono font-bold">ONLINE</span>
                </div>
                {isSpeaking && (
                    <button
                        onClick={stopSpeaking}
                        className="text-[10px] tracking-wider text-cyan-400 font-mono px-2 py-0.5 rounded border border-cyan-500/40 bg-cyan-950/60 hover:bg-cyan-900/60 cursor-pointer animate-pulse"
                    >
                        [STOP AUDIO]
                    </button>
                )}
            </div>

            {/* The Orb Container */}
            <div 
                className="relative flex items-center justify-center w-14 h-14 sm:w-16 sm:h-16 cursor-pointer"
                onClick={() => {
                    if (isSpeaking && stopSpeaking) stopSpeaking();
                }}
                title={isSpeaking ? "Click to stop speaking" : "Grace Core"}
            >
                {/* Expanding Sonar Rings */}
                <motion.div
                    className={`absolute inset-0 rounded-full border ${isSpeaking ? 'border-cyan-400/70' : 'border-cyan-500/30'}`}
                    animate={{ scale: isSpeaking ? [1, 2.8] : [1, 2.3], opacity: [0.8, 0] }}
                    transition={{ duration: isSpeaking ? 1.2 : 3, repeat: Infinity, ease: "easeOut", delay: 0 }}
                />
                
                <motion.div
                    className={`absolute inset-0 rounded-full border ${isSpeaking ? 'border-cyan-300/50' : 'border-cyan-400/20'}`}
                    animate={{ scale: isSpeaking ? [1, 2.8] : [1, 2.3], opacity: [0.8, 0] }}
                    transition={{ duration: isSpeaking ? 1.2 : 3, repeat: Infinity, ease: "easeOut", delay: isSpeaking ? 0.4 : 1 }}
                />

                <motion.div
                    className={`absolute inset-0 rounded-full border ${isSpeaking ? 'border-cyan-500/40' : 'border-cyan-600/20'}`}
                    animate={{ scale: isSpeaking ? [1, 2.8] : [1, 2.3], opacity: [0.8, 0] }}
                    transition={{ duration: isSpeaking ? 1.2 : 3, repeat: Infinity, ease: "easeOut", delay: isSpeaking ? 0.8 : 2 }}
                />

                {/* Solid Core Orb */}
                <motion.div
                    animate={{ 
                        scale: isSpeaking ? [1, 1.25, 1] : [1, 1.08, 1], 
                        opacity: [0.85, 1, 0.85] 
                    }}
                    transition={{ duration: isSpeaking ? 0.6 : 2, repeat: Infinity, ease: "easeInOut" }}
                    className="relative w-8 h-8 sm:w-9 sm:h-9 rounded-full border-2 border-cyan-400 shadow-[0_0_20px_rgba(0,212,255,0.7)] bg-cyan-950 flex items-center justify-center"
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
