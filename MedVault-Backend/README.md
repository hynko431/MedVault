# MedVault Backend

Backend API service for **MedVault – Secure Medical Records Vault**.

This backend handles authentication, family member management, prescription uploads, reminders, and notifications.

---

## Tech Stack

* Node.js
* Express.js
* PostgreSQL
* JWT Authentication
* AWS S3 (for prescription uploads)
* Node-Cron (for reminders)
* REST API

---

## Project Structure

```text
src
│
├── config
│   └── db.js
│
├── routes
│   ├── auth.routes.js
│   ├── family.routes.js
│   ├── prescription.routes.js
│   ├── reminder.routes.js
│   └── notification.routes.js
│
├── middlewares
│   └── auth.middleware.js
│
├── utils
│   └── jwt.utils.js
│
├── cron
│   └── reminder.cron.js
│
├── app.js
└── server.js
```

---

## Installation

Clone the repository:

```bash
git clone https://github.com/asarittechnologies/MedVault.git
```

Go to backend folder:

```bash
cd medvault-backend
```

Install dependencies:

```bash
npm install
```

---

## Environment Variables

Create a `.env` file in the root directory.

Example:

```bash
PORT=5000
DATABASE_URL=your_postgresql_connection_string
JWT_SECRET=your_secret_key
AWS_ACCESS_KEY=your_access_key
AWS_SECRET_KEY=your_secret_key
AWS_BUCKET_NAME=your_bucket
AI_OCR_SERVICE_URL=http://ai_ocr_service:8000
```

---

## Running the Server

Development mode:

```bash
npm run dev
```

Production mode:

```bash
node src/server.js
```

Server will run at:

```text
http://localhost:5000
```

---

## API Test

Test if backend is running:

```text
GET /
```

Response:

```json
{
  "message": "MedVault backend is running"
}
```

Test endpoint:

```text
GET /api/test
```

Response:

```json
{
  "message": "Backend API working correctly"
}
```

---

## API Modules

### Authentication

```text
/api/auth
```

### Family Members

```text
/api/family
```

### Prescription Upload

```text
/api/prescriptions
```

### Reminders

```text
/api/reminders
```

### Notifications

```text
/api/notifications
```

### File Upload (S3)

```text
/api/s3
```

---

## Features

* Secure user authentication
* Family member management
* Prescription storage (PostgreSQL metadata)
* Medicine reminders
* Notification system
* Secure file uploads to AWS S3

---

## Cron Jobs

Reminder notifications are handled using **node-cron**.

```javascript
src/cron/reminder.cron.js
```

This automatically triggers reminder checks.

---

## Author

Akash
MedVault Project
