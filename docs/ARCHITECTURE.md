# CivicFlow — System Architecture & Specification

> **Version:** 1.0 (Phase 0 Freeze)  
> **Status:** APPROVED & FROZEN  
> **Scope:** Complete architectural blueprint for the CivicFlow platform

---

## 1. Executive Summary & Problem Space

CivicFlow is an AI-assisted civic complaint intake and adjudication platform designed for municipal public service. In conventional municipal reporting, citizens submit complaints using informal phrasing, localized slang, incomplete context, vague addresses, and uncurated photos. Municipal triage teams waste critical time decoding unclear submissions, leading to backlogs, misrouted tasks, and citizen disillusionment.

CivicFlow bridges this divide through:
1. **Multimodal AI Intake**: Grounded multimodal analysis via Google Gemini API to structure physical evidence and citizen intent into a professional municipal draft.
2. **Deterministic Geographic Context**: Device GPS coordinates and reverse geocoding provide verifiable location context, with automated mismatch detection between stated addresses and telemetry.
3. **Mandatory Human-in-the-Loop (HITL)**: The citizen reviews, corrects, and authorizes the AI draft prior to official municipal submission.
4. **Authoritative Administrative Control**: Municipal administrators review full provenance (raw citizen text, uploaded photo, AI draft, citizen final submission, and map context) to make binding acceptance or rejection decisions.

---

## 2. High-Level System Architecture

The system is architected as a robust, high-performance monolith to eliminate unnecessary distributed systems overhead while ensuring strict domain separation.

```text
┌────────────────────────────────────────────────────────────────────────┐
│                        CLIENT LAYER (SPA)                              │
│  React 18 + Vite + Tailwind CSS + Lucide Icons + Leaflet (OSM)         │
│  • Citizen Mobile-First Portal (Intake, Review & Tracking)             │
│  • Municipal Admin Desktop Portal (Triage, Map Viewer, Decision Panel) │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ HTTPS / REST (JSON + Multipart)
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        API GATEWAY / FASTAPI                           │
│  FastAPI (Python 3.10+) + Pydantic v2 + OAuth2 Password Bearer / JWT   │
├────────────────────────────────────────────────────────────────────────┤
│  Routing & Security Middleware:                                        │
│  • /api/v1/auth          (Register, Login, Token, Current User)        │
│  • /api/v1/complaints    (Intake, Gemini Draft, Citizen Edit, Submit)  │
│  • /api/v1/admin         (Triage Queue, Adjudication, Metrics)        │
│  • /api/v1/notifications (Citizen Decision Alerts)                     │
└───────────┬───────────────────────┬───────────────────────────┬────────┘
            │                       │                           │
            ▼                       ▼                           ▼
┌──────────────────────┐ ┌──────────────────────┐ ┌──────────────────────┐
│     AI SERVICE       │ │   LOCATION SERVICE   │ │  DATABASE & STORAGE  │
│  Google Gemini API   │ │  OpenStreetMap /     │ │  PostgreSQL / SQLite │
│  (google-genai SDK)  │ │  Nominatim API       │ │  SQLAlchemy ORM      │
│  • Multimodal Vision │ │  • Reverse Geocode   │ │  Local Static Uploads│
│  • Grounded Struct   │ │  • Discrepancy Check │ │  (MIME & Hash Valid) │
│  • Strict Pydantic   │ │  • Map URL Generator │ │                      │
└──────────────────────┘ └──────────────────────┘ └──────────────────────┘
```

---

## 3. Strict Domain Boundaries & Separation of Concerns

To guarantee honesty and eliminate fabricated intelligence, strict operational boundaries are enforced across system components:

| Responsibility | Handled By | Explicitly Forbidden |
| :--- | :--- | :--- |
| **Physical Evidence Understanding** | Gemini Multimodal API | Generating fake summary, hallucinating measurements, assuming road ownership |
| **Citizen Intent Normalization** | Gemini Language Model | Changing citizen meaning, inventing facts not in user statement |
| **Coordinates & Geolocation** | Device Telemetry (HTML5 Geolocation) | AI guessing or inventing latitude/longitude |
| **Address Verification & Map Link** | Backend Location Service (Nominatim) | LLM generating arbitrary map links or geocoding |
| **Complaint Lifecycle & State** | FastAPI State Machine | Client-side status mutations, bypassing review |
| **Administrative Adjudication** | Human Municipal Admin | AI automatically approving/rejecting complaints |
| **Authentication & Authorization** | FastAPI + JWT + Bcrypt/Argon2 | Storing plaintext passwords, exposing API keys to frontend |

---

## 4. Complaint Finite State Machine (FSM)

A complaint must strictly follow the defined state machine. Arbitrary transitions or backwards mutations from terminal states are blocked at the ORM/Service layer.

```text
                        ┌──────────────┐
                        │    DRAFT     │  (Citizen enters initial data & photo)
                        └──────┬───────┘
                               │ POST /complaints/analyze
                               ▼
                        ┌──────────────┐
                        │ AI_GENERATED │  (Gemini extracts structured report)
                        └──────┬───────┘
                               │ PUT /complaints/{id}/draft
                               ▼
                        ┌──────────────┐
                        │ UNDER_REVIEW │  (Citizen reviews, edits, and verifies)
                        └──────┬───────┘
                               │ POST /complaints/{id}/submit
                               ▼
                        ┌──────────────┐
                        │  SUBMITTED   │  (Lodged with municipality for triage)
                        └──────┬───────┘
                               │
               ┌───────────────┴───────────────┐
               │ Admin Accept                  │ Admin Reject
               ▼                               ▼
       ┌──────────────┐                ┌──────────────┐
       │   ACCEPTED   │                │   REJECTED   │
       └──────────────┘                └──────────────┘
```

### Transition Validation Matrix

| Current State | Target State | Allowed Actor | Trigger Action |
| :--- | :--- | :--- | :--- |
| `DRAFT` | `AI_GENERATED` | Citizen (Owner) | Backend receives photo & description; invokes Gemini API |
| `AI_GENERATED` | `UNDER_REVIEW` | Citizen (Owner) | Citizen opens draft for editing |
| `UNDER_REVIEW` | `UNDER_REVIEW` | Citizen (Owner) | Citizen modifies problem, address, or summary |
| `UNDER_REVIEW` | `SUBMITTED` | Citizen (Owner) | Citizen clicks "Submit to Municipality" |
| `SUBMITTED` | `ACCEPTED` | Admin | Admin validates evidence and accepts complaint |
| `SUBMITTED` | `REJECTED` | Admin | Admin rejects complaint with mandatory justification |
| `ACCEPTED` | *Any* | None | **FORBIDDEN** (Terminal state) |
| `REJECTED` | *Any* | None | **FORBIDDEN** (Terminal state) |

---

## 5. Multimodal AI Agent Specification

### 5.1 Provider & SDK
- Provider: Google Gemini API
- SDK: Official Google GenAI SDK (`google-genai`)
- Model Default: `gemini-2.5-flash` (configurable via `GEMINI_MODEL` environment variable)

### 5.2 Reasoning Principles & Constraints
1. **Evidence Grounding**: The AI may only use physical observations visible in the uploaded image and claims stated in the citizen description.
2. **Distinction of Observation vs. Claim**:
   - *Observed*: "Image reveals an unpaved asphalt crater approximately across half the lane width."
   - *Claimed*: "Citizen reports that their scooter tire was damaged at this location."
3. **Prohibition of Hallucinations**:
   - DO NOT invent pothole depth or millimeter measurements unless a physical ruler is visible.
   - DO NOT invent municipality names, road codes, accident records, or traffic volumes.
   - DO NOT invent dates, previous repair histories, or contractor names.
4. **Structured Output Enforcement**:
   - The model must respond strictly in JSON matching the `GeminiComplaintDraft` Pydantic schema.
   - If the model produces invalid JSON or schema violations, the service retries exactly once with a corrective error feedback prompt. If it fails a second time, the system aborts with a graceful user-facing error.

### 5.3 Error Handling & Fallback Policy
- **No Mock Responses**: If the Gemini API fails, network is unreachable, or the key is invalid, the system returns HTTP 502 with a clear error: `"Unable to prepare the report draft at this moment. Please check your connection or try again."`
- Under no circumstances will the service return pre-scripted "canned" AI drafts.

---

## 6. Geographic & Location Intelligence Engine

### 6.1 Telemetry Origin
Coordinates are acquired via browser `navigator.geolocation.getCurrentPosition()`. Coordinates are transmitted as numerical IEEE 754 floating-point values.

### 6.2 Reverse Geocoding & Validation Flow
1. **Device Coordinates Acquired**: `(latitude, longitude)`
2. **Reverse Geocoding via Nominatim**:
   - Query: `GET https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lon}&format=jsonv2`
   - Header: Custom `User-Agent: CivicFlow/1.0 (civicflow-dev@users.noreply.github.com)` per OSM Usage Policy.
   - Output: Formatted address string, administrative district, postcode, place ID.
3. **Address Mismatch Detection**:
   - If citizen's text address significantly deviates from reverse-geocoded address (e.g., citizen types "North District Main Road" but GPS indicates "South Industrial Corridor"), the system flags `location_status = "MISMATCH_SUSPECTED"`.
   - The UI surfaces this neutrally to the citizen: *"The submitted address appears different from your device's current location. Please verify before submitting."*
4. **Map URL Generation**:
   - Deterministic OpenStreetMap URL: `https://www.openstreetmap.org/?mlat={lat}&mlon={lon}#map=17/{lat}/{lon}`
   - Embedded interactive viewer powered by Leaflet tiles.
5. **Location Semantics & Address Re-Edit Handling**:
   - Strict distinction is maintained between:
     - `original_latitude`/`original_longitude`: Device-reported incident coordinates at capture.
     - `typed/geocoded address`: Text address entered or modified by citizen.
   - If the citizen edits their address, the device-reported coordinates are **never silently overwritten**. Instead, the geocoded address coordinates are evaluated separately, and any discrepancy is captured in `location_status` for administrative transparency.

---

## 7. Human-in-the-Loop (HITL) Review Flow

CivicFlow treats AI as a drafting assistant, not an automated submission authority.

```text
[ Citizen Intake Form ]
       │ (Upload photo, enter informal description, provide address hint, share GPS)
       ▼
[ AI Draft Generation ]
       │ (Gemini processes inputs -> generates structured draft)
       ▼
[ Review Screen (HITL) ]
       │
       ├── Original Photo Preview (Fixed)
       ├── Problem Description [EDITABLE INPUT]
       ├── Formal Municipal Summary [EDITABLE TEXTAREA]
       ├── Incident Address [EDITABLE INPUT]
       └── Interactive Map & Coordinates [READ-ONLY VERIFICATION]
       │
       ▼
[ Citizen Authorizes & Clicks "Submit Complaint" ]
```

---

## 8. Municipal Admin Review & Decision Subsystem

The Municipal Admin Portal is designed for calm, unambiguous decision-making:
- **Triage Queue**: Sortable by submission date, category, and review status.
- **Evidence Inspection**:
  - Raw citizen statement vs. final citizen-reviewed text.
  - Full-resolution uploaded photograph.
  - Interactive OpenStreetMap pin with accurate coordinates.
  - Location status indicator (e.g., `VERIFIED_COORDINATES`, `MISMATCH_FLAGGED`).
- **Adjudication Actions**:
  - **Accept**: Moves complaint to `ACCEPTED`. Admin provides target resolution unit and notes.
  - **Reject**: Moves complaint to `REJECTED`. Admin must provide a constructive rationale (e.g., "Private property dispute", "Duplicate report", "Insufficient location information").

---

## 9. Notification Subsystem

- When an administrator accepts or rejects a complaint, an internal notification record is generated immediately in the `notifications` table.
- Citizen dashboard displays unread notification counters and clickable alert cards.
- Endpoints:
  - `GET /api/v1/notifications`: List notifications for current authenticated citizen.
  - `PATCH /api/v1/notifications/{id}/read`: Mark notification as read.

---

## 10. Security, Privacy & Data Integrity

1. **Secret Isolation**:
   - Gemini API keys, JWT secret keys, and database credentials exist exclusively in `.env`.
   - Frontend never receives or proxies secrets.
2. **Authentication & Password Security**:
   - Passwords hashed with `bcrypt` (or `argon2id`) with minimum cost factor 12.
   - JWT tokens signed with HS256, expiration enforced (1440 minutes default).
3. **Role-Based Access Control (RBAC)**:
   - `Role.CITIZEN`: Can only create drafts, edit their own drafts, submit their own complaints, view their own complaint history, and view their own notifications.
   - `Role.ADMIN`: Can view all submitted complaints, execute accept/reject transitions, and view municipal analytics.
4. **Asset Upload Hygiene**:
   - Accepted MIME types: `image/jpeg`, `image/png`, `image/webp`.
   - Strict file size cap: 10 MB.
   - Storage filename sanitization using UUID4 + extension (prevents path traversal).
5. **No Hallucinated Evidence Policy**:
   - Database explicitly preserves `original_problem`, `original_address`, `ai_problem`, `ai_summary`, and `final_problem`, `final_summary` as distinct fields for complete auditability.
