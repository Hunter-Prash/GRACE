import express from 'express';
import jwt from 'jsonwebtoken';
import nodemailer from 'nodemailer';
import crypto from 'crypto';

const router = express.Router();

// A simple in-memory cache for magic links since it's serverless, 
// wait, no, serverless means this memory disappears between cold starts.
// For a personal AI, if we don't have DynamoDB for this, we can just use 
// a signed JWT as the magic link token itself!

router.post('/login', (req, res) => {
    const { email, password } = req.body;

    if (!email || !password) {
        return res.status(400).json({ error: 'Email and password are required' });
    }

    if (email === process.env.WEB_AUTH_EMAIL && password === process.env.WEB_AUTH_PASSWORD) {
        const token = jwt.sign(
            { email: process.env.WEB_AUTH_EMAIL },
            process.env.JWT_SECRET,
            { expiresIn: '30d' } // Token valid for 30 days
        );
        return res.json({ token, message: 'Login successful' });
    }

    return res.status(401).json({ error: 'Invalid credentials' });
});

router.post('/forgot-password', async (req, res) => {
    const { email } = req.body;

    if (email !== process.env.WEB_AUTH_EMAIL) {
        // Always return success to prevent email enumeration
        return res.json({ message: 'If the email exists, a magic link was sent.' });
    }

    try {
        // Create a magic link token valid for 15 minutes
        const magicToken = jwt.sign(
            { email: process.env.WEB_AUTH_EMAIL, magic: true },
            process.env.JWT_SECRET,
            { expiresIn: '15m' }
        );

        // Note: In production you would want the frontend domain, but we can just use 
        // the host or expect the client to pass the base URL.
        const origin = req.headers.origin || 'http://localhost:5173';
        const magicLink = `${origin}?magicToken=${magicToken}`;

        const transporter = nodemailer.createTransport({
            service: 'gmail',
            auth: {
                user: process.env.WEB_AUTH_EMAIL,
                pass: process.env.GMAIL_APP_PASSWORD
            }
        });

        const mailOptions = {
            from: process.env.WEB_AUTH_EMAIL,
            to: process.env.WEB_AUTH_EMAIL,
            subject: 'Grace Web Portal - Magic Login Link',
            text: `You requested a magic link to login to Grace.\n\nClick here to login securely: ${magicLink}\n\nThis link expires in 15 minutes.`
        };

        await transporter.sendMail(mailOptions);

        return res.json({ message: 'If the email exists, a magic link was sent.' });
    } catch (error) {
        console.error("[AUTH] Error sending magic link:", error);
        return res.status(500).json({ error: 'Failed to send email' });
    }
});

// Endpoint for frontend to exchange magic token for a real 30-day token
router.post('/magic-login', (req, res) => {
    const { magicToken } = req.body;
    
    if (!magicToken) return res.status(400).json({ error: 'No token provided' });

    try {
        const decoded = jwt.verify(magicToken, process.env.JWT_SECRET);
        
        if (!decoded.magic) return res.status(401).json({ error: 'Invalid magic token' });
        if (decoded.email !== process.env.WEB_AUTH_EMAIL) return res.status(401).json({ error: 'Invalid user' });

        // Issue real token
        const token = jwt.sign(
            { email: process.env.WEB_AUTH_EMAIL },
            process.env.JWT_SECRET,
            { expiresIn: '30d' }
        );
        
        return res.json({ token, message: 'Magic login successful' });
    } catch (error) {
        return res.status(401).json({ error: 'Invalid or expired magic link' });
    }
});

export default router;
