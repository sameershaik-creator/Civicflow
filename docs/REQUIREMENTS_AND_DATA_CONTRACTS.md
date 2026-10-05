# CivicFlow — Data Contracts & Requirements Specification

> **Version:** 1.0 (Phase 0 Freeze)  
> **Status:** APPROVED & FROZEN  
> **Scope:** Pydantic models, Database entity definitions, and REST API contract specification

---

## 1. Relational Database Schema (SQLAlchemy ORM)

### 1.1 `users` Table
| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `VARCHAR(36)` | PRIMARY KEY | UUIDv4 identifier |
| `name` | `VARCHAR(128)` | NOT NULL | Citizen or official's full name |
| `email` | `VARCHAR(255)` | NOT NULL, UNIQUE, INDEX | Unique email address |
| `password_hash`| `VARCHAR(255)` | NOT NULL | Bcrypt hash |
| `role` | `VARCHAR(20)` | NOT NULL, DEFAULT `'citizen'` | `citizen` or `admin` |
| `created_at` | `TIMESTAMP` | NOT NULL, UTC DEFAULT | Account registration timestamp |

### 1.2 `complaints` Table
| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `VARCHAR(36)` | PRIMARY KEY | UUIDv4 identifier |
| `user_id` | `VARCHAR(36)` | NOT NULL, FK(`users.id`), INDEX | Complaint author (citizen) |
| `image_url` | `VARCHAR(512)` | NOT NULL | Path/URL to uploaded evidence image |
| `original_problem`| `TEXT` | NOT NULL | Raw citizen description as typed |
| `original_address`| `VARCHAR(512)` | NULLABLE | Initial address hint entered by citizen |
| `original_latitude`| `FLOAT` | NULLABLE | Latitude reported by device at intake |
| `original_longitude`| `FLOAT` | NULLABLE | Longitude reported by device at intake |
| `ai_problem` | `TEXT` | NULLABLE | Structured problem synthesized by Gemini |
| `ai_address` | `VARCHAR(512)` | NULLABLE | Address verified/standardized by AI/Geo |
| `ai_summary` | `TEXT` | NULLABLE | Formal municipal complaint draft from Gemini |
| `final_problem` | `TEXT` | NULLABLE | Citizen's edited problem prior to submit |
| `final_address` | `VARCHAR(512)` | NULLABLE | Citizen's edited address prior to submit |
| `final_summary` | `TEXT` | NULLABLE | Citizen's edited formal summary |
| `latitude` | `FLOAT` | NULLABLE | Authoritative incident latitude |
| `longitude` | `FLOAT` | NULLABLE | Authoritative incident longitude |
| `place_id` | `VARCHAR(128)` | NULLABLE | Nominatim OSM place identifier |
| `map_url` | `VARCHAR(512)` | NULLABLE | Deterministic OpenStreetMap viewer URL |
| `location_status` | `VARCHAR(50)` | NOT NULL, DEFAULT `'COORDINATES_ATTACHED'` | e.g. `COORDINATES_ATTACHED`, `MISMATCH_FLAGGED`, `NO_LOCATION` |
| `status` | `VARCHAR(30)` | NOT NULL, DEFAULT `'DRAFT'` | Finite state machine enum |
| `admin_reason` | `TEXT` | NULLABLE | Official acceptance or rejection notes |
| `created_at` | `TIMESTAMP` | NOT NULL, UTC DEFAULT | Intake initiation timestamp |
| `updated_at` | `TIMESTAMP` | NOT NULL, UTC DEFAULT | Last draft modification timestamp |
| `submitted_at` | `TIMESTAMP` | NULLABLE | Official municipal submission timestamp |
| `decided_at` | `TIMESTAMP` | NULLABLE | Municipal admin decision timestamp |

### 1.3 `notifications` Table
| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `VARCHAR(36)` | PRIMARY KEY | UUIDv4 identifier |
| `user_id` | `VARCHAR(36)` | NOT NULL, FK(`users.id`), INDEX | Target citizen |
| `complaint_id` | `VARCHAR(36)` | NOT NULL, FK(`complaints.id`) | Referenced complaint |
| `title` | `VARCHAR(255)` | NOT NULL | Notification headline |
| `message` | `TEXT` | NOT NULL | Notification body explaining decision |
| `is_read` | `BOOLEAN` | NOT NULL, DEFAULT `FALSE` | Read status |
| `created_at` | `TIMESTAMP` | NOT NULL, UTC DEFAULT | Alert creation timestamp |

---

## 2. Gemini Multimodal Structured Output Schema

The Gemini AI model is strictly bound to this Pydantic schema using structured JSON mode:

```python
from pydantic import BaseModel, Field
from typing import List, Optional

class GeminiComplaintDraft(BaseModel):
    category: str = Field(
        description="Standard municipal category e.g. Roads & Pavements, Sanitation, Water Supply, Street Lighting, Drainage, Public Hazard."
    )
    observed_issue: str = Field(
        description="Objective description of the physical defect directly visible in the image."
    )
    citizen_claim: str = Field(
        description="Professional articulation of what the citizen is reporting without inventing facts."
    )
    formal_summary: str = Field(
        description="A clear, professional, respectful municipal complaint ready for public works triage."
    )
    urgency_level: str = Field(
        description="Assessed triage level: 'LOW', 'MEDIUM', 'HIGH', or 'CRITICAL', based strictly on visible hazards."
    )
    warnings: List[str] = Field(
        default_factory=list,
        description="Any noticed inconsistencies, poor lighting warnings, or missing details."
    )
```

---

## 3. REST API Contracts & Endpoint Specifications

### 3.1 Authentication (`/api/v1/auth`)
- `POST /api/v1/auth/register`
  - **Body**: `{ name: str, email: EmailStr, password: str, role: Optional[str] = "citizen" }`
  - **Response (201)**: `{ user: { id, name, email, role }, access_token: str, token_type: "bearer" }`
- `POST /api/v1/auth/login`
  - **Body**: Form data / JSON `{ username: email, password: password }`
  - **Response (200)**: `{ user: { id, name, email, role }, access_token: str, token_type: "bearer" }`
- `GET /api/v1/auth/me`
  - **Headers**: `Authorization: Bearer <token>`
  - **Response (200)**: `{ id, name, email, role, created_at }`

### 3.2 Complaint Intake & Drafting (`/api/v1/complaints`)
- `POST /api/v1/complaints/analyze`
  - **Headers**: `Authorization: Bearer <token>`
  - **Form Data**:
    - `image`: File (JPEG, PNG, WebP)
    - `description`: String (citizen informal description)
    - `address`: Optional String (address hint)
    - `latitude`: Optional Float (device GPS)
    - `longitude`: Optional Float (device GPS)
  - **Response (201)**: Complete Complaint object in state `AI_GENERATED`.
- `PUT /api/v1/complaints/{id}/draft`
  - **Headers**: `Authorization: Bearer <token>` (Must be owner)
  - **Body**: `{ final_problem: str, final_address: str, final_summary: str }`
  - **Response (200)**: Updated Complaint object in state `UNDER_REVIEW`.
- `POST /api/v1/complaints/{id}/submit`
  - **Headers**: `Authorization: Bearer <token>` (Must be owner)
  - **Response (200)**: Complaint object transitioned to `SUBMITTED`, with `submitted_at` timestamp recorded.
- `GET /api/v1/complaints`
  - **Headers**: `Authorization: Bearer <token>`
  - **Response (200)**: List of complaints belonging to the current authenticated citizen.
- `GET /api/v1/complaints/{id}`
  - **Headers**: `Authorization: Bearer <token>`
  - **Response (200)**: Full details of the complaint (restricted to owner or admin).

### 3.3 Administrative Adjudication (`/api/v1/admin`)
- `GET /api/v1/admin/complaints`
  - **Headers**: `Authorization: Bearer <token>` (Must be `admin`)
  - **Query Params**: `status` filter, `sort` order, `limit`, `offset`
  - **Response (200)**: All municipal complaints with user details and provenance.
- `POST /api/v1/admin/complaints/{id}/accept`
  - **Headers**: `Authorization: Bearer <token>` (Must be `admin`)
  - **Body**: `{ reason: str, assigned_department: Optional[str] }`
  - **Response (200)**: Complaint transitioned to `ACCEPTED`, with notification triggered.
- `POST /api/v1/admin/complaints/{id}/reject`
  - **Headers**: `Authorization: Bearer <token>` (Must be `admin`)
  - **Body**: `{ reason: str }` (Mandatory justification)
  - **Response (200)**: Complaint transitioned to `REJECTED`, with notification triggered.

### 3.4 Notifications (`/api/v1/notifications`)
- `GET /api/v1/notifications`
  - **Headers**: `Authorization: Bearer <token>`
  - **Response (200)**: List of notifications for current citizen, sorted by `created_at` DESC.
- `PATCH /api/v1/notifications/{id}/read`
  - **Headers**: `Authorization: Bearer <token>`
  - **Response (200)**: Updated notification object with `is_read: True`.

---

## 4. UI/UX Aesthetic Principles & Style Guide

Per Master Prompt Section 15-18:
1. **Calm Public Service Aesthetic**:
   - Palette: Deep slate (`#0f172a`), crisp municipal navy (`#1e3a8a`), clean neutral whites/grays (`#f8fafc`, `#e2e8f0`), accessible emerald for acceptance (`#059669`), and sober amber/crimson for alerts (`#b91c1c`).
   - High-contrast, clean typography (Inter / System Sans-serif).
   - Clear visual boundaries, generous padding, readable line heights.
2. **Prohibited Patterns**:
   - No glowing AI cards or neon borders.
   - No "AI Engine Activated", "Vision Agent Running", or fake terminal spinners.
   - Natural human copy: *"Preparing your draft report..."*, *"Review & Edit"*, *"Submit to Municipality"*.
