const express = require("express");
const router = express.Router();
const pool = require("../config/db");
const authMiddleware = require("../middlewares/auth.middleware");

router.get("/", authMiddleware, async (req, res) => {
    const userId = req.user.userId;

    const result = await pool.query(
        `SELECT id, title, message, created_at
         FROM notifications
         WHERE user_id = $1
         ORDER BY created_at DESC`,
        [userId]
    );

    res.json(result.rows);
});

module.exports = router;
