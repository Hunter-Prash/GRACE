import React from 'react'
import { motion } from 'framer-motion'

const Chatlog = ({ messages, bottomRef }) => {
    return (
        <div className="flex-1 overflow-y-auto p-3 sm:p-4 md:p-8 space-y-4 sm:space-y-6 max-w-3xl mx-auto w-full relative z-10">
            {messages?.map((item, idx) => {
                
                // Generate a realistic sequential time based on the index offset
                const time = new Date(Date.now() - (messages.length - 1 - idx) * 60000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

                return (
                    item.role === 'user' ? (<>
                        <motion.div
                            key={idx}
                            className="flex flex-col items-end self-end ml-auto max-w-[95%] sm:max-w-[85%]"
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ duration: 0.2 }}
                        >
                            <div className="flex items-center gap-2 mb-1">
                                <span className="text-[10px] tracking-widest text-fuchsia-500/50 font-mono">{time}</span>
                                <span className="text-[10px] sm:text-xs tracking-widest text-fuchsia-500 font-bold drop-shadow-[0_0_8px_rgba(217,70,239,0.8)]">YOU</span>
                            </div>
                            <div className="bg-[#1a0515]/80 backdrop-blur-sm border border-fuchsia-500/80 text-fuchsia-50 px-3 py-2 sm:px-4 sm:py-3 rounded-lg leading-relaxed shadow-[0_0_15px_rgba(217,70,239,0.3),inset_0_0_10px_rgba(217,70,239,0.15)] text-sm sm:text-base">
                                <p className="whitespace-pre-wrap break-words">{item.parts[0].text}</p>
                            </div>
                        </motion.div>
                    </>) :


                        (<motion.div
                            key={idx}
                            className="flex flex-col items-start self-start mr-auto max-w-[95%] sm:max-w-[85%]"
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ duration: 0.2 }}
                        >
                            <div className="flex items-center gap-2 mb-1">
                                <span className="text-[10px] sm:text-xs tracking-widest text-cyan-400 font-bold drop-shadow-[0_0_8px_rgba(34,211,238,0.8)]">GRACE</span>
                                <span className="text-[10px] tracking-widest text-cyan-500/50 font-mono">{time}</span>
                            </div>
                            <div className="bg-[#05151a]/80 backdrop-blur-sm border border-cyan-400/80 text-cyan-50 px-3 py-2 sm:px-4 sm:py-3 rounded-lg leading-relaxed shadow-[0_0_15px_rgba(34,211,238,0.3),inset_0_0_10px_rgba(34,211,238,0.15)] text-sm sm:text-base relative overflow-hidden">
                                {/* Holographic Scanning Line */}
                                <motion.div 
                                    className="absolute left-0 right-0 h-[1px] bg-cyan-400/20 shadow-[0_0_10px_rgba(34,211,238,0.2)] pointer-events-none z-0"
                                    animate={{ top: ["-50%", "150%"] }}
                                    transition={{ duration: 3, repeat: Infinity, ease: "linear" }}
                                />
                                <p className="whitespace-pre-wrap break-words relative z-10">{item.parts[0].text}</p>
                            </div>
                        </motion.div>)

                )
            })}
            <div ref={bottomRef} />
        </div>
    )
}

export default Chatlog