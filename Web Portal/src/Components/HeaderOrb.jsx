import React from 'react';
import { motion } from 'framer-motion';

const HeaderOrb = () => {
    return (
        <header className="flex flex-col items-center justify-center p-4 sm:p-6 pb-12 sm:pb-16 bg-gradient-to-b from-[#020404] via-[#020404]/90 to-transparent shrink-0 z-10 relative -mb-8 sm:-mb-10 pointer-events-none">
            
            {/* The Orb Container */}
            <div className="relative flex items-center justify-center w-16 h-16 sm:w-20 sm:h-20">
                
                {/* Expanding Sonar Ring 1 */}
                <motion.div
                    className="absolute inset-0 rounded-full border border-cyan-500/30"
                    animate={{ scale: [1, 2.5], opacity: [0.8, 0] }}
                    transition={{ duration: 3, repeat: Infinity, ease: "easeOut", delay: 0 }}
                />
                
                {/* Expanding Sonar Ring 2 */}
                <motion.div
                    className="absolute inset-0 rounded-full border border-cyan-400/20"
                    animate={{ scale: [1, 2.5], opacity: [0.8, 0] }}
                    transition={{ duration: 3, repeat: Infinity, ease: "easeOut", delay: 1 }}
                />

                {/* Expanding Sonar Ring 3 */}
                <motion.div
                    className="absolute inset-0 rounded-full border border-cyan-600/20"
                    animate={{ scale: [1, 2.5], opacity: [0.8, 0] }}
                    transition={{ duration: 3, repeat: Infinity, ease: "easeOut", delay: 2 }}
                />

                {/* Solid Core Orb */}
                <motion.div
                    animate={{ scale: [1, 1.1, 1], opacity: [0.8, 1, 0.8] }}
                    transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
                    className="relative w-8 h-8 sm:w-10 sm:h-10 rounded-full border-2 border-cyan-400 shadow-[0_0_20px_rgba(0,212,255,0.6)] bg-cyan-950 flex items-center justify-center"
                >
                    {/* Inner intense glow */}
                    <div className="w-full h-full rounded-full bg-cyan-400/20 blur-[2px]" />
                </motion.div>
            </div>

            <h1 className="mt-1 sm:mt-2 text-[10px] sm:text-xs tracking-[0.3em] text-cyan-500/70 font-bold uppercase drop-shadow-[0_0_5px_rgba(0,212,255,0.3)]">
                GRACE
            </h1>
        </header>
    );
};

export default HeaderOrb;
