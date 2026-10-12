# AI-Based Student Answer Evaluation Portal - Frontend

This is the React-based frontend for the AI-Powered Answer Script Evaluation System. It communicates with the FastAPI backend to provide dashboards for both professors and students.

## Requirements

- Node.js (v18+ recommended)
- npm (v9+)
- Python 3.9+ (for the backend)
- PostgreSQL (for the backend database)

## Installation

```bash
# Navigate to the frontend directory
cd frontend

# Install dependencies
npm install
```

## Environment Configuration

Copy the example environment file and configure it:

```bash
cp .env.example .env
```

Ensure the following variables are set correctly in your `.env` file:
```
VITE_API_BASE_URL=http://localhost:8001
```

*(Note: The FastAPI backend must be running on the specified URL. Do not expose internal server paths, AI keys, or JWT secrets in this file. All security keys are managed exclusively by the backend.)*

## Running the Application

### Development Server
Run the local Vite development server:
```bash
npm run dev
```
The application will be accessible at `http://localhost:5173`.

### Production Build
To create a production-ready optimized build:
```bash
npm run build
```
The compiled static files will be placed in the `dist/` directory.

## Backend Requirement

The frontend is strictly a UI layer. The FastAPI backend **must** be running to handle authentication, role-based authorization, PDF uploads, OCR, AI evaluation, and database interactions.

```bash
# Example backend run command
cd ../backend
uvicorn app.main:app --port 8001 --reload
```

## Security & Architecture

- **Token Storage**: JWT tokens are managed in `localStorage` securely and automatically attached via Axios interceptors.
- **Route Protection**: The application enforces role-based client-side routing (`Professor` vs `Student`).
- **Data Isolation**: The frontend exclusively uses the backend's authorized endpoints (e.g., `/students/me/results`), ensuring students cannot manipulate URLs to view private data.
- **AI Evaluation**: The frontend orchestrates the asynchronous AI pipelines sequentially (`process` → `ocr` → `extract` → `evaluate`) ensuring data consistency without simulating or inventing fake responses.
