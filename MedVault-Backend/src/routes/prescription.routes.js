const express = require("express");
const router = express.Router();
const pool = require("../config/db");
const authMiddleware = require("../middlewares/auth.middleware");
const { generateDownloadURL } = require("../services/s3Service");

/* ─────────────────────────────────────────────────────────────
   Helper: call the AI OCR microservice
   Uses Node 18's built-in globalThis.fetch (no extra deps needed)
───────────────────────────────────────────────────────────── */
const OCR_SERVICE_URL = process.env.AI_OCR_SERVICE_URL || "http://ai_ocr_service:8000";

async function triggerOCR(prescriptionId, s3FileKey) {
    // Generate a short-lived presigned download URL for the OCR service
    const imageUrl = await generateDownloadURL(s3FileKey);

    const response = await fetch(`${OCR_SERVICE_URL}/ocr/extract`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            prescription_id: String(prescriptionId),
            image_url: imageUrl,
        }),
    });

    if (!response.ok) {
        const errorBody = await response.text();
        throw new Error(`OCR service returned ${response.status}: ${errorBody}`);
    }

    return response.json(); // { prescription_id, raw_text, cleaned_text, extracted_data, processing_time_ms }
}

/* =========================
   SAVE PRESCRIPTION + TRIGGER OCR
   POST /api/prescriptions/upload
   ========================= */
router.post("/upload", authMiddleware, async (req, res) => {
    try {
        const { family_member_id, file_key } = req.body;
        const userId = req.user.userId;

        if (!family_member_id || !file_key) {
            return res.status(400).json({
                message: "family_member_id and file_key are required",
            });
        }

        // 1️⃣ Save prescription metadata
        const result = await pool.query(
            `INSERT INTO prescriptions (user_id, family_member_id, file_key, status)
             VALUES ($1, $2, $3, 'PROCESSING')
             RETURNING id, status`,
            [userId, family_member_id, file_key]
        );

        const prescriptionId = result.rows[0].id;

        // 2️⃣ Call AI OCR service synchronously
        let ocrResult = null;
        let finalStatus = "PROCESSING";

        try {
            ocrResult = await triggerOCR(prescriptionId, file_key);
            finalStatus = "COMPLETE";

            // 3️⃣ Persist OCR output to prescription_ocr table
            await pool.query(
                `INSERT INTO prescription_ocr (prescription_id, raw_text, structured_data)
                 VALUES ($1, $2, $3)
                 ON CONFLICT (prescription_id) DO UPDATE
                   SET raw_text = EXCLUDED.raw_text,
                       structured_data = EXCLUDED.structured_data`,
                [
                    prescriptionId,
                    ocrResult.raw_text,
                    JSON.stringify(ocrResult.extracted_data),
                ]
            );

            // 4️⃣ Mark prescription as COMPLETE
            await pool.query(
                `UPDATE prescriptions SET status = 'COMPLETE' WHERE id = $1`,
                [prescriptionId]
            );
        } catch (ocrError) {
            console.error("OCR pipeline failed for prescription", prescriptionId, ocrError.message);
            // Update status to FAILED so frontend can show an error state
            await pool.query(
                `UPDATE prescriptions SET status = 'FAILED' WHERE id = $1`,
                [prescriptionId]
            );
            finalStatus = "FAILED";
        }

        res.json({
            prescriptionId,
            status: finalStatus,
            ...(ocrResult && { extractedData: ocrResult.extracted_data }),
        });

    } catch (error) {
        console.error(error.message);
        res.status(500).json({ error: error.message });
    }
});

/* =========================
   LIST PRESCRIPTIONS
   GET /api/prescriptions
   ========================= */
router.get("/", authMiddleware, async (req, res) => {
    try {
        const userId = req.user.userId;

        const result = await pool.query(
            `SELECT id, family_member_id, file_key, status, created_at
             FROM prescriptions
             WHERE user_id = $1
             ORDER BY created_at DESC`,
            [userId]
        );

        res.json(result.rows);
    } catch (error) {
        console.error(error.message);
        res.status(500).json({ error: error.message });
    }
});

/* =========================
   SEARCH PRESCRIPTIONS (via Elasticsearch)
   GET /api/prescriptions/search?q=amoxicillin
   ========================= */
router.get("/search", authMiddleware, async (req, res) => {
    try {
        const { q, size = 10 } = req.query;

        if (!q || !q.trim()) {
            return res.status(400).json({ message: "Query parameter 'q' is required." });
        }

        // Proxy to OCR service Elasticsearch search
        const ocrResponse = await fetch(
            `${OCR_SERVICE_URL}/search/prescriptions?q=${encodeURIComponent(q)}&size=${size}`
        );

        if (!ocrResponse.ok) {
            const err = await ocrResponse.text();
            return res.status(502).json({ message: `Search service error: ${err}` });
        }

        const data = await ocrResponse.json();
        res.json(data);

    } catch (error) {
        console.error(error.message);
        res.status(500).json({ error: error.message });
    }
});

/* =========================
   GET SINGLE PRESCRIPTION
   GET /api/prescriptions/:id
   ========================= */
router.get("/:id", authMiddleware, async (req, res) => {
    try {
        const userId = req.user.userId;
        const prescriptionId = req.params.id;

        const result = await pool.query(
            `SELECT p.id, p.family_member_id, p.file_key, p.status, p.created_at,
                    o.raw_text, o.structured_data
             FROM prescriptions p
             LEFT JOIN prescription_ocr o
               ON p.id = o.prescription_id
             WHERE p.id = $1 AND p.user_id = $2`,
            [prescriptionId, userId]
        );

        if (result.rows.length === 0) {
            return res.status(404).json({ message: "Prescription not found" });
        }

        res.json(result.rows[0]);
    } catch (error) {
        console.error(error.message);
        res.status(500).json({ error: error.message });
    }
});

module.exports = router;
