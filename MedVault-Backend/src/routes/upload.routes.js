const express = require("express");
const router = express.Router();
const {
    generateUploadURL,
    generateDownloadURL,
} = require("../services/s3Service");

// Get pre-signed upload URL
router.post("/get-upload-url", async (req, res) => {
    try {
        const { fileName, fileType } = req.body;

        if (!fileName || !fileType) {
            return res.status(400).json({
                message: "fileName and fileType are required",
            });
        }

        const { uploadURL, key } = await generateUploadURL(fileName, fileType);

        res.json({
            uploadURL,
            fileKey: key,
        });
    } catch (error) {
        res.status(500).json({ message: error.message });
    }
});

// Get pre-signed download URL
router.post("/get-download-url", async (req, res) => {
    try {
        const { fileKey } = req.body;

        if (!fileKey) {
            return res.status(400).json({
                message: "fileKey is required",
            });
        }

        const downloadURL = await generateDownloadURL(fileKey);

        res.json({ downloadURL });
    } catch (error) {
        res.status(500).json({ message: error.message });
    }
});

module.exports = router;
