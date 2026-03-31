# MedVault Backend

Backend API service for **MedVault – Secure Medical Records Vault**.

This backend handles authentication, family member management, prescription uploads, reminders, and notifications.

---

## Tech Stack

* Node.js
* Express.js
* MongoDB
* JWT Authentication
* AWS S3 (for prescription uploads)
* Node-Cron (for reminders)
* REST API

---

## Project Structure

```
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

```
git clone https://github.com/asarittechnologies/MedVault.git
```

Go to backend folder:

```
cd medvault-backend
```

Install dependencies:

```
npm install
```

---

## Environment Variables

Create a `.env` file in the root directory.

Example:

```
PORT=5000
MONGO_URI=your_mongodb_connection
JWT_SECRET=your_secret_key
AWS_ACCESS_KEY=your_access_key
AWS_SECRET_KEY=your_secret_key
AWS_BUCKET_NAME=your_bucket
```

---

## Running the Server

Development mode:

```
npm run dev
```

Production mode:

```
node src/server.js
```

Server will run at:

```
http://localhost:5000
```

---

## API Test

Test if backend is running:

```
GET /
```

Response:

```
{
  "message": "MedVault backend is running"
}
```

Test endpoint:

```
GET /api/test
```

Response:

```
{
  "message": "Backend API working correctly"
}
```

---

## API Modules

### Authentication

```
/api/auth
```

### Family Members

```
/api/family
```

### Prescription Upload

```
/api/prescriptions
```

### Reminders

```
/api/reminders
```

### Notifications

```
/api/notifications
```

### File Upload (S3)

```
/api/s3
```

---

## Features

* Secure user authentication
* Family member management
* Prescription storage
* Medicine reminders
* Notification system
* Secure file uploads to AWS S3

---

## Cron Jobs

Reminder notifications are handled using **node-cron**.

```
src/cron/reminder.cron.js
```

This automatically triggers reminder checks.

---

## Author

Akash
MedVault Project
