# CivicFlow

> **An AI-assisted civic complaint system that converts messy citizen reports into clear, professional complaints while keeping the citizen and municipal administrator in control.**

---

## 1. Product Overview

CivicFlow addresses a fundamental challenge in civic governance: citizens often report critical municipal problems (potholes, water leaks, broken streetlights, illegal dumping) using informal language, slang, vague addresses, and unstructured photos. Municipal administrators are overwhelmed with poorly articulated reports, leading to delayed triage and unresolved grievances.

CivicFlow integrates a **real multimodal AI pipeline (Google Gemini API)** with **real geographic validation (Leaflet / OpenStreetMap / Nominatim)** and a **mandatory Human-in-the-Loop review process**.

### Core Workflow

```text
Citizen
   │  • Problem photograph
   │  • Informal description
   │  • Address hint
   │  • Device GPS coordinates
   ▼
CivicFlow Backend
   │  • Multimodal Gemini Analysis (Structured Pydantic validation)
   │  • Geographic & Reverse Geocoding Analysis
   ▼
Professional Complaint Draft
   │
   ▼
Citizen Reviews & Edits (Human-in-the-Loop)
   │
   ▼
Citizen Submits
   │
   ▼
Municipal Admin Dashboard
   │  ├── Accept (with resolution notes)
   │  └── Reject (with constructive rationale)
   ▼
Citizen In-App Notification
```

---

## 2. Core Architectural Principles

1. **Zero Hardcoded AI**: No fake summaries, mock scores, or pre-scripted classifications. Live Gemini calls only, backed by strict Pydantic parsing and controlled error handling.
2. **Zero Fake Location Data**: Coordinates originate from real device telemetry. Geographic resolution and map links are computed deterministically, never hallucinated by LLMs.
3. **Citizen Authority**: AI creates a draft; the citizen remains the ultimate author and authorizer before municipal submission.
4. **Administrative Finality**: Administrators retain final adjudication authority; AI never acts as a government adjudicator.
5. **Calm Public-Service UX**: Trustworthy, accessible, high-contrast, professional design without gimmicky "AI agent" theatrics.

---

## 3. Technology Stack

- **Frontend**: React 18, Vite, Tailwind CSS, Lucide React, Leaflet & React-Leaflet
- **Backend**: Python 3.10+, FastAPI, Pydantic v2, SQLAlchemy ORM, Uvicorn
- **Database**: PostgreSQL (with SQLite compatibility for local sandbox testing)
- **AI Engine**: Google Gemini API (`google-genai` / `google-generativeai`)
- **Mapping & Geocoding**: OpenStreetMap Tile Service, Nominatim Reverse Geocoding API
- **Authentication**: JWT (JSON Web Tokens) with Argon2/Bcrypt password hashing and Role-Based Access Control (`citizen`, `admin`)

---

## 4. Project Roadmap & Phases

- [x] **Phase 0**: Requirements + Architecture Freeze *(Current)*
- [ ] **Phase 1**: Repository + Development Environment Setup
- [ ] **Phase 2**: Database Schema + ORM Models + Migrations
- [ ] **Phase 3**: Authentication & RBAC (Citizen & Admin)
- [ ] **Phase 4**: Citizen Complaint Intake & Asset Upload Pipeline
- [ ] **Phase 5**: Real Gemini Multimodal AI Agent Integration
- [ ] **Phase 6**: Geographic Verification & Interactive Map Engine
- [ ] **Phase 7**: AI Draft Generation & Human-in-the-Loop Review UI
- [ ] **Phase 8**: Submission Pipeline & Strict Complaint State Machine
- [ ] **Phase 9**: Municipal Admin Dashboard & Decision Engine
- [ ] **Phase 10**: Citizen In-App Notification System
- [ ] **Phase 11**: Security Hardening, Audit & Comprehensive Test Suite
- [ ] **Phase 12**: UI Polish, Accessibility, & End-to-End Demo Readiness

---

## 5. Documentation Links

- [Architecture Specification](file:///c:/Users/SKAIK%20SAMEER/CivicFlow/docs/ARCHITECTURE.md)
- [Requirements & Data Contracts](file:///c:/Users/SKAIK%20SAMEER/CivicFlow/docs/REQUIREMENTS_AND_DATA_CONTRACTS.md)
