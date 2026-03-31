const cron = require("node-cron");
const pool = require("../config/db");

console.log("🚀 REMINDER CRON FILE LOADED");

cron.schedule("* * * * *", async () => {
    console.log("⏱ CRON RUNNING AT", new Date());

    try {
        const now = new Date();

        const result = await pool.query(
            `SELECT id, user_id, title
             FROM reminders
             WHERE reminder_time <= $1
             AND is_active = true`,
            [now]
        );

        console.log("FOUND REMINDERS:", result.rows.length);

        for (const reminder of result.rows) {
            await pool.query(
                `INSERT INTO notifications (user_id, title, message)
                 VALUES ($1, $2, $3)`,
                [reminder.user_id, "Medicine Reminder", reminder.title]
            );

            await pool.query(
                `UPDATE reminders SET is_active = false WHERE id = $1`,
                [reminder.id]
            );

            console.log("🔔 Notification created for", reminder.title);
        }

    } catch (error) {
        console.error("CRON ERROR:", error.message);
    }
});
