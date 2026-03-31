const { S3Client, PutObjectCommand, GetObjectCommand } = require("@aws-sdk/client-s3");
const { getSignedUrl } = require("@aws-sdk/s3-request-presigner");

const s3Client = new S3Client({
    region: process.env.AWS_REGION,
    credentials: {
        accessKeyId: process.env.AWS_ACCESS_KEY_ID,
        secretAccessKey: process.env.AWS_SECRET_ACCESS_KEY,
    },
});

// Generate pre-signed upload URL
async function generateUploadURL(fileName, fileType) {
    const key = `prescriptions/${Date.now()}_${fileName}`;

    const command = new PutObjectCommand({
        Bucket: process.env.S3_BUCKET_NAME,
        Key: key,
        ContentType: fileType,
    });

    const uploadURL = await getSignedUrl(s3Client, command, { expiresIn: 300 });

    return { uploadURL, key };
}

// Generate pre-signed download URL
async function generateDownloadURL(fileKey) {
    const command = new GetObjectCommand({
        Bucket: process.env.S3_BUCKET_NAME,
        Key: fileKey,
    });

    const downloadURL = await getSignedUrl(s3Client, command, { expiresIn: 3600 });

    return downloadURL;
}

module.exports = {
    generateUploadURL,
    generateDownloadURL,
};
