# Hotel Client Request Platform — Frontend

Next.js (App Router) + TypeScript + Tailwind + shadcn/ui frontend for the
Hotel Client Request Platform. Talks to the Django REST backend built
alongside it.

Two portals: **Guest** and **Operator**. Admin uses Django Admin directly
(no separate admin frontend, per the original spec).

## Requirements

- Node.js 20+
- The Django backend running locally (see the backend repo's README)

## Setup

```bash
npm install
cp .env.local.example .env.local
# edit .env.local if your backend isn't on http://127.0.0.1:8000
npm run dev
```

Open http://localhost:3000 — you should see a connection-status card
confirming the backend is reachable.

## Design tokens

Custom warm teal + brass palette (not the default shadcn theme), RTL-first,
Vazirmatn typeface (self-hosted via `@fontsource-variable/vazirmatn`, matching
the Hotel Extensions project's font choice). Tokens live in
`src/app/globals.css`.

## Project layout

```
src/
├── app/            # App Router pages
├── components/
│   └── ui/         # shadcn-style primitives (hand-added; the shadcn
│                    # CLI registry isn't reachable from this dev sandbox,
│                    # so components are added manually following its
│                    # standard structure)
└── lib/            # cn() helper, API client (added in later phases)
```

Development follows a phased plan (F1–F11) — see the project's
implementation plan for what each phase adds.
