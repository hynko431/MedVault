const express = require("express");
const router = express.Router();
const pool = require("../config/db");
const auth = require("../middlewares/auth.middleware");

router.get("/", auth, async (req, res) => {
    const userId = req.user.userId;

    const result = await pool.query(
        "SELECT id,name,relation,age FROM family_members WHERE user_id=$1",
        [userId]
    );

    res.json(result.rows);
});

router.post("/", auth, async (req, res) => {
    const { name, relation, age } = req.body;
    const userId = req.user.userId;

    await pool.query(
        "INSERT INTO family_members (user_id,name,relation,age) VALUES ($1,$2,$3,$4)",
        [userId, name, relation || null, age || null]
    );

    res.json({ message: "Family member added" });
});

module.exports = router;
