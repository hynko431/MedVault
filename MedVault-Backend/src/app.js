require("dotenv").config();

const express = require("express");
const cors = require("cors");

const authRoutes = require("./routes/auth.routes");
const familyRoutes = require("./routes/family.routes");
const uploadRoutes = require("./routes/upload.routes");
const prescriptionRoutes = require("./routes/prescription.routes");
const reminderRoutes = require("./routes/reminder.routes");
const notificationRoutes = require("./routes/notification.routes");

const app = express();

/* ========================
   MIDDLEWARE
======================== */

app.use(
    cors({
        origin: "http://localhost:8081", // frontend URL
        credentials: true,
    })
);

app.use(express.json());

/* ========================
   ROUTES
======================== */

app.use("/api/auth", authRoutes);
app.use("/api/family", familyRoutes);
app.use("/api/s3", uploadRoutes);
app.use("/api/prescriptions", prescriptionRoutes);
app.use("/api/reminders", reminderRoutes);
app.use("/api/notifications", notificationRoutes);

// Cron
require("./cron/reminder.cron");

/* ========================
   TEST ROUTES
======================== */

app.get("/api/test", (req, res) => {
    res.json({
        status: "success",
        message: "Backend API working correctly",
    });
});

/* ========================
   ERROR HANDLER
======================== */

app.use((err, req, res, next) => {
    console.error("SERVER ERROR:", err);
    res.status(500).json({
        status: "error",
        message: "Internal Server Error",
    });
});

module.exports = app;