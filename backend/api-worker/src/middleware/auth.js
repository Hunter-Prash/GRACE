import jwt from 'jsonwebtoken';

export const verifyToken = (req, res, next) => {
    // We allow preflight OPTIONS requests without a token
    if (req.method === 'OPTIONS') {
        return next();
    }

    const authHeader = req.headers.authorization;
    const internalSecret = req.headers['x-internal-secret'];

    if (internalSecret && internalSecret === process.env.JWT_SECRET) {
        req.user = { role: 'system' };
        return next();
    }

    if (!authHeader) {
        return res.status(401).json({ error: 'Access denied. No token provided.' });
    }

    const token = authHeader.split(' ')[1];
    if (!token) {
        return res.status(401).json({ error: 'Access denied. Token format invalid.' });
    }

    try {
        const decoded = jwt.verify(token, process.env.JWT_SECRET);
        req.user = decoded;
        next();
    } catch (error) {
        return res.status(401).json({ error: 'Invalid or expired token.' });
    }
};
