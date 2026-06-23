import { useState, useRef, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Send, Mic } from 'lucide-react';
import axios from 'axios'
import Chatlog from './Components/Chatlog';
import InputBox from './Components/InputBox';
import HeaderOrb from './Components/HeaderOrb';

export default function App() {

    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState('');
    const bottomRef = useRef(null);
    const [loading, setLoading] = useState(false)


    const handleSend = async (e) => {
        e.preventDefault()
        if (!input) return
        setLoading(true)
        try {

            setMessages((prev) => [...prev, {
                role: 'user',
                parts: [{ text: input }]
            }]);

            const response = await axios.post(
                "https://y32tddvhc0.execute-api.ap-south-1.amazonaws.com/Prod/api/chat",
                { text: input }
            )

            console.log(response.data.text)

            // Append GRACE's response
            setMessages((prev) => [...prev, {
                role: 'model',
                parts: [{ text: response.data.text }]
            }]);

            setInput("")
            setLoading(false)

        } catch (error) {
            console.log(error)
        }

    }

    useEffect(() => {
        const fetchChat = async () => {
            try {
                let response = await axios.get("https://y32tddvhc0.execute-api.ap-south-1.amazonaws.com/Prod/api/history/default")
                console.log(response.data.history)
                setMessages(response.data.history)
            } catch (e) {
                console.log(e)
            }
        }
        fetchChat()
    }, [])

    //sam deploy --stack-name grace-backend-stack --no-confirm-changeset --resolve-s3 --capabilities CAPABILITY_IAM

    return (
        <div className="relative flex flex-col h-[100dvh] bg-[#020404] text-cyan-50 font-sans selection:bg-cyan-900 selection:text-cyan-50 overflow-hidden">

            {/* Animated Cyber Grid Background */}
            <div className="absolute inset-0 cyber-grid animate-grid pointer-events-none z-0"></div>

            <HeaderOrb />

            <Chatlog messages={messages} bottomRef={bottomRef} />


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
            />

        </div>
    );
}
