# ChronoCIT — University Timetable & Venue ERP

[![Live on Vercel](https://img.shields.io/badge/Vercel-Deployed_Live-000000?style=for-the-badge&logo=vercel&logoColor=white)](https://cit-campus-erp.vercel.app)
[![Python 3.12](https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Hard Violations](https://img.shields.io/badge/Hard_Violations-0_Clashes-10B981?style=for-the-badge)](https://cit-campus-erp.vercel.app/admin)
[![Spectra Score](https://img.shields.io/badge/Spectra_Score-63.0%20%2F%2064.0-6366F1?style=for-the-badge)](https://cit-campus-erp.vercel.app/admin)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](LICENSE)

**ChronoCIT** is an enterprise campus scheduling, venue management, and emergency disruption engine built for the **Chilika Institute of Technology (CIT)** to resolve **"Crunch Week"** (Week 7: 189 teaching classes, annual tech fest Spectra, and midsem exam preparations).

---

## 🌐 Live Production Deployment

| Portal / Route | Public URL | Description |
| :--- | :--- | :--- |
| **Student & Faculty Portal** | [cit-campus-erp.vercel.app](https://cit-campus-erp.vercel.app/) | Interactive 5-day timetable grid, natural language venue requests, live status pills |
| **Dedicated User Login** | [cit-campus-erp.vercel.app/login](https://cit-campus-erp.vercel.app/login) | Student, Faculty & Club authorization in White-Maroon-Yellow institutional palette |
| **Dedicated Admin Clearance** | [cit-campus-erp.vercel.app/admin/login](https://cit-campus-erp.vercel.app/admin/login) | Guarded administrator login with interactive captcha and password masking |
| **Private Admin Terminal** | [cit-campus-erp.vercel.app/admin](https://cit-campus-erp.vercel.app/admin) | Schedule matrix, emergency room-leak rerouting, soft penalty metrics, validator runner |

---

## 🏛️ System Architecture

```text
┌────────────────────────────────────────────────────────────────────────┐
│                        ChronoCIT Frontend (SPA)                        │
│   Semantic White & Maroon Palette · Realtime Timetable · Filter Engine │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ HTTP / REST
┌───────────────────────────────────▼────────────────────────────────────┐
│                  Serverless Python Core (/api/index.py)                │
│             Zero Cold-Start · Multi-Threaded Local Server.py           │
├───────────────────┬───────────────────────────────┬────────────────────┤
│  Constraint Engine│      AI Booking Concierge     │ Disruption Manager │
│  0 Hard Clashes   │  English + Hinglish NLP Parser│ Minimal Move Diff  │
│  MRV & CP-SAT     │   Deterministic Code Checks   │  Room Preservation │
└─────────┬─────────┴───────────────┬───────────────┴──────────┬─────────┘
          │                         │                          │
┌─────────▼─────────────────────────▼──────────────────────────▼─────────┐
│              Official Crunch Week Validator (validator.py)             │
│        Certified: 0 Hard Violations · 63.0/64 Booking Score            │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Key Features

### 1. Master Timetable Grid (0 Hard Violations)
- **189 sessions** (243 teaching hours/week) across 27 venues and 40 faculty.
- Clear 3-color status system:
  - 🟩 **Green (`#15803d`)**: Available / Active confirmed sessions.
  - ⬜ **Grey (`#4b5563`)**: Upcoming scheduled sessions.
  - 🟥 **Red (`#b91c1c`)**: Cancelled / Disrupted sessions rerouted elsewhere.
- Clean 5-day view (Monday–Friday) with empty weekend columns eliminated.
- Multi-dimensional filtering by **Student Cohort** (14 groups), **Faculty** (40 faculty), and **Venues** (27 rooms).

### 2. Spectra Fest Venue Manager (Week 7)
- Processes 25 booking requests adhering strictly to institutional priority:
  $$\text{Exams} > \text{Regular Classes} > \text{Institute Events} > \text{Guest Lectures} > \text{Department Events} > \text{Club Events}$$
- Resolves ties via `submitted_at` timestamps and honors `role_category_cap`.
- **Score: 63.0 / 64 max** (20 Approved, 3 Alternatives Offered, 2 Rejected with explicit valid reasons, 0 Priority Inversions).

### 3. AI Natural Language Venue Concierge (English & Hinglish)
- Accurately parses freeform user text:
  - *"Need auditorium for 250 pax on Friday 6 to 8 pm with projector and sound"*
  - *"seminar hall kal shaam 6 baje, 2 ghante, 100 log, mic chahiye"*
- Auto-extracts capacity, duration periods, day, equipment requirements, and venue categories.
- **Deterministic Code Guardrail**: The LLM parses natural language intent, but constraint checks and booking confirmations are strictly executed in verified code.

### 4. Disruption & Minimal-Move Rescheduler
- Automatically resolves simulated real-world disruptions (`sample_disruption.json`):
  - Room **CR-102** water-leak emergency unavailability.
  - Faculty **F07** sudden medical leave.
  - Urgent session **CS202-T2** insertion.
- **0 Time Shifts**: All 11 disrupted sessions are rerouted to alternative rooms at the exact same hour with zero timetable displacement for students.

### 5. Strict Route Isolation & Security
- User dashboard and login screens contain zero administrative icons or links.
- Unauthorized attempts to access `/admin` trigger an automatic redirection to `/admin/login`.
- Admin login features security captcha validation and password visibility toggle.

---

## 👥 Demo Personas

| Role | Test Email | Default Password | Permissions |
| :--- | :--- | :--- | :--- |
| **Dean (Admin)** | `admin@cit.ac.in` | Any | Full access: disruption approvals, priority matrix, validator runner |
| **Faculty Member** | `faculty.f19@cit.ac.in` | Any | View faculty timetable, moved sessions, personal commitments |
| **Student Lead** | `student@cit.ac.in` | Any | Cohort timetable, submit NLP bookings, track approval status |
| **Club Lead** | `spectra.club@cit.ac.in` | Any | Fest venue reservation, equipment requests |

---

## 🛠️ Local Development & Quick Start

### Prerequisites
- Python 3.8+ (No external dependencies required; pure standard library).

```bash
# 1. Clone the repository
git clone https://github.com/abhisar-dev/cit-campus-erp.git
cd cit-campus-erp

# 2. Start local multi-threaded development server
python server.py
```
Open **`http://localhost:8000`** in your browser.

---

## 📁 Repository Structure

```text
cit-campus-erp/
├── .github/workflows/       # GitHub Actions automated constraint validation
├── api/
│   └── index.py            # Serverless Python entrypoint for Vercel
├── assets/                  # Public assets, images, baseline datasets
│   ├── cit_login_bg.jpg    # Student login visual background
│   ├── admin_login_left.jpg# Admin vector illustration artwork
│   ├── cit_public.json     # Master institute dataset
│   └── sample_disruption.json
├── exports/
│   ├── schedule.json       # Baseline scheduled timetable (0 hard clashes)
│   └── schedule_after.json # Repaired schedule after Week 7 disruption
├── admin.html               # Private Admin Dashboard
├── admin_login.html         # Private Admin Clearance Login
├── index.html               # Student / User Interactive Portal
├── login.html               # Student / User Login
├── server.py                # Standalone multi-threaded Python ERP server
├── validator.py             # Official Crunch Week constraint validation runner
└── vercel.json              # Vercel serverless routing & deployment config
```

---

## 📄 License
This project is open-source under the [MIT License](LICENSE).
