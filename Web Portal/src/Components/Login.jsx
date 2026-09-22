import React, { useState } from 'react';
import axios from 'axios';
import { motion } from 'framer-motion';

export default function Login({ setToken }) {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [loading, setLoading] = useState(false);
    const [message, setMessage] = useState('');
    const [isForgot, setIsForgot] = useState(false);

    // Hardcode backend url for local testing until it's in .env
    const BACKEND_URL = "https://y32tddvhc0.execute-api.ap-south-1.amazonaws.com/Prod";

    const handleLogin = async (e) => {
        e.preventDefault();
        setLoading(true);
        setMessage('');
        try {
            const res = await axios.post(`${BACKEND_URL}/api/auth/login`, { email, password });
            const { token } = res.data;
            localStorage.setItem('grace_token', token);
            setToken(token);
        } catch (error) {
            setMessage(error.response?.data?.error || 'Login failed');
        }
        setLoading(false);
    };

    const handleForgot = async (e) => {
        e.preventDefault();
        if (!email) {
            setMessage("Please enter your email first.");
            return;
        }
        setLoading(true);
        setMessage('');
        try {
            const res = await axios.post(`${BACKEND_URL}/api/auth/forgot-password`, { email });
            setMessage(res.data.message);
        } catch (error) {
            setMessage('Failed to send magic link');
        }
        setLoading(false);
    };

    return (
        <div className="flex flex-col items-center justify-center min-h-[100dvh] bg-[#020404] text-cyan-50 relative overflow-hidden">
            <div className="absolute inset-0 cyber-grid animate-grid pointer-events-none z-0"></div>
            
            <motion.div 
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="z-10 bg-cyan-950/20 p-8 rounded-2xl border border-cyan-500/30 shadow-[0_0_30px_rgba(34,211,238,0.1)] backdrop-blur-xl w-full max-w-md"
            >
                <div className="flex flex-col items-center mb-8">
                    <div className="w-16 h-16 rounded-full bg-cyan-500/20 border border-cyan-400 shadow-[0_0_15px_rgba(34,211,238,0.5)] flex items-center justify-center mb-4">
                        <div className="w-8 h-8 rounded-full bg-cyan-400 animate-pulse shadow-[0_0_10px_rgba(34,211,238,0.8)]"></div>
                    </div>
                    <h1 className="text-2xl font-bold tracking-widest text-cyan-300">GRACE OS</h1>
                    <p className="text-cyan-600 text-sm mt-1 uppercase tracking-wider">{isForgot ? 'Magic Link Recovery' : 'Secure Login'}</p>
                </div>

                <form onSubmit={isForgot ? handleForgot : handleLogin} className="flex flex-col gap-4">
                    <input 
                        type="email" 
                        placeholder="Email Address" 
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        required
                        className="bg-black/50 border border-cyan-900 rounded-lg px-4 py-3 outline-none focus:border-cyan-400 focus:shadow-[0_0_10px_rgba(34,211,238,0.3)] transition-all"
                    />
                    
                    {!isForgot && (
                        <input 
                            type="password" 
                            placeholder="Password" 
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            required
                            className="bg-black/50 border border-cyan-900 rounded-lg px-4 py-3 outline-none focus:border-cyan-400 focus:shadow-[0_0_10px_rgba(34,211,238,0.3)] transition-all"
                        />
                    )}

                    <button 
                        type="submit" 
                        disabled={loading}
                        className="mt-2 bg-cyan-600 hover:bg-cyan-500 text-black font-bold py-3 rounded-lg shadow-[0_0_15px_rgba(34,211,238,0.4)] transition-all disabled:opacity-50 cursor-pointer"
                    >
                        {loading ? 'Processing...' : (isForgot ? 'Send Magic Link' : 'Initialize')}
                    </button>
                </form>

                {message && (
                    <p className="mt-4 text-center text-sm text-cyan-300 bg-cyan-950/50 py-2 px-4 rounded-lg border border-cyan-800">
                        {message}
                    </p>
                )}

                <div className="mt-6 text-center">
                    <button 
                        type="button"
                        onClick={() => { setIsForgot(!isForgot); setMessage(''); }}
                        className="text-cyan-700 hover:text-cyan-400 text-sm tracking-wide transition-colors cursor-pointer"
                    >
                        {isForgot ? 'Back to Login' : 'Forgot Password?'}
                    </button>
                </div>
            </motion.div>
        </div>
    );
}
