const express = require("express");
const router = express.Router();
const pool = require("../config/db");
const authMiddleware = require("../middlewares/auth.middleware");

/* =========================
   ADD REMINDER
   ========================= */
router.post("/", authMiddleware, async (req, res) => {
    try {
        const { title, reminder_time } = req.body;
        const userId = req.user.userId;

        if (!title || !reminder_time) {
            return res.status(400).json({ message: "Title and reminder_time required" });
        }

        await pool.query(
            `INSERT INTO reminders (user_id, title, reminder_time)
             VALUES ($1, $2, $3)`,
            [userId, title, reminder_time]
        );

        res.json({ message: "Reminder added successfully" });

    } catch (error) {
        console.error(error.message);
        res.status(500).json({ error: error.message });
    }
});

/* =========================
   LIST REMINDERS
   ========================= */
router.get("/", authMiddleware, async (req, res) => {
    try {
        const userId = req.user.userId;

        const result = await pool.query(
            `SELECT id, title, reminder_time, is_active
             FROM reminders
             WHERE user_id = $1
             ORDER BY reminder_time ASC`,
            [userId]
        );

        res.json(result.rows);

    } catch (error) {
        console.error(error.message);
        res.status(500).json({ error: error.message });
    }
});

module.exports = router;
