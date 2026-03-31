const express = require("express");
const router = express.Router();
const pool = require("../config/db");
const { generateToken } = require("../utils/jwt.utils");

/* SEND OTP */
router.post("/mobile/send-otp", async (req, res) => {
    const { mobile } = req.body;

    if (!mobile) {
        return res.status(400).json({ message: "Mobile required" });
    }

    res.json({
        message: "OTP sent",
        otp: "1234",
    });
});

/* VERIFY OTP */
router.post("/mobile/verify-otp", async (req, res) => {
    const { mobile, otp } = req.body;

    if (!mobile || !otp) {
        return res.status(400).json({ message: "Mobile & OTP required" });
    }

    if (otp !== "1234") {
        return res.status(401).json({ message: "Invalid OTP" });
    }

    let user = await pool.query(
        "SELECT id FROM users WHERE mobile=$1",
        [mobile]
    );

    if (user.rows.length === 0) {
        const created = await pool.query(
            "INSERT INTO users (mobile, auth_provider) VALUES ($1,$2) RETURNING id",
            [mobile, "mobile"]
        );
        user = { rows: [created.rows[0]] };
    }

    const token = generateToken({
        userId: user.rows[0].id,
        auth_provider: "mobile",
    });

    res.json({ token });
});

module.exports = router;
