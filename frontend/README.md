# Sherman Travel Assistant - Frontend

Vue 3 frontend for the Sherman Travel Assistant application.

## Setup

1. Install dependencies:
```bash
npm install
```

2. Start development server:
```bash
npm run dev
```

The app will be available at `http://localhost:5173`

## Build for Production

```bash
npm run build
```

The built files will be in the `dist/` directory.

## Environment Variables

Create a `.env` file in the frontend directory:

```
VITE_API_BASE_URL=http://localhost:8000/api
```

## Project Structure

```
frontend/
├── src/
│   ├── components/     # Vue components
│   ├── services/       # API services
│   ├── App.vue         # Main app component
│   ├── main.js         # App entry point
│   └── style.css       # Global styles
├── index.html
├── package.json
└── vite.config.js
```

