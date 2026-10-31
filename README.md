# ChronoCIT — University Timetable & Venue ERP

**ChronoCIT** is an enterprise campus scheduling and venue management platform built for the **Chilika Institute of Technology (CIT)** to solve "Crunch Week" (Week 7: teaching classes, annual tech fest Spectra, and midsem exam preparations).

---

## 🏛️ System Architecture

```text
┌────────────────────────────────────────────────────────────────────────┐
│                        ChronoCIT Frontend (SPA)                       │
│      React 18 · Tailwind CSS · Motion Aware · Multi-Role Switcher      │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ HTTP / REST
┌───────────────────────────────────▼────────────────────────────────────┐
│                    ChronoCIT Core Service (Python)                     │
│               Lightweight Server · Dynamic REST Endpoints              │
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

1. **Master Timetable Grid (0 Hard Violations)**:
   - 189 sessions (243 teaching hours/week) across 27 venues and 40 faculty.
   - Filterable by **Student Group** (14 groups), **Faculty** (40 faculty), or **Room** (27 venues).
   - Color-coded badges for Lectures, Tutorials, 3-Hour Labs (anchored strictly at P2 or P6), and Open Elective Baskets.

2. **Spectra Fest Venue Manager (Week 7)**:
   - Processes all 25 booking requests according to institutional priority:
     `Exams > Regular Classes > Institute Events > Guest Lectures > Department Events > Club Events`
   - Handles ties with `submitted_at` timestamps and honors `role_category_cap`.
   - **Score: 63.0 / 64 max** (20 Approved, 3 Alternatives Offered, 2 Rejected with explicit valid reasons, 0 Priority Inversions).

3. **AI Booking Concierge (English & Hinglish)**:
   - Understands unstructured natural language requests (e.g., *"seminar hall kal shaam 6 baje, 2 ghante, 100 log, mic chahiye"*).
   - Generates an editable preview card and prompts follow-up questions for ambiguous inputs.
   - **Code-Based Verification**: The LLM never validates bookings; all requests pass through deterministic constraint code.
   - Fallback manual booking form provided for 100% offline resilience.

4. **Disruption & Minimal-Move Rescheduler**:
   - Handles real-world disruptions (e.g., `sample_disruption.json`: Room CR-102 flooded, Faculty F07 leave, session CS202-T2 added).
   - Achieves **0 time-slot shifts** (all 11 classes moved to available alternative rooms at the exact same hour).
   - Side-by-side diff comparison and 1-click Admin approval.

5. **Midsem Exam Matrix**:
   - Schedules 41 midsem exams across Monday–Saturday in AM and PM sessions.
   - Automatically halves room capacities for exam seating validation.

---

## 👥 Demo Accounts (Evaluator Quick Logins)

The top command bar features instant 1-click persona switching:

| Role | Persona | Permissions |
| :--- | :--- | :--- |
| **Admin (Dean's Office)** | **Prof. A. Sengupta** | Full control: timetable generation, disruption approval, priority order, demo reset. |
| **Department Coordinator** | **Dr. R. K. Mishra (CSE)** | Department session requests, lab approvals, venue booking. |
| **Faculty** | **Dr. S. N. Bose (F19)** | View personal timetable, unavailability preferences, moved sessions. |
| **Club Representative** | **Aryan Sharma (Dramatics)** | Submit plain-language/Hinglish venue requests, track approval status and reasons. |

> **Reset Demo Data**: An explicit red **Reset Demo** button is situated at the top right for judges to return the system to the initial baseline state at any time.

---

## 🛠️ Tech Stack & Setup Instructions

### Prerequisites
- Python 3.8+ (Zero extra pip packages required; Google OR-Tools optional).
- Modern web browser (Chrome, Edge, Firefox).

### Run Locally
```bash
# Clone the repository
git clone <repo-url>
cd cit-campus-erp

# Run the ChronoCIT ERP server
python server.py
```
Open your browser and navigate to:
**`http://localhost:8000`**

---

## 📁 Submission Artifacts

- **`exports/schedule.json`**: Certified baseline timetable, midsem exams, and Spectra week bookings (0 hard violations).
- **`exports/schedule_after.json`**: Repaired timetable after applying `sample_disruption.json` (0 hard violations, 0 time shifts, 11 room-only moves).
- **`AI_USAGE.md`**: Complete disclosure of AI tools and in-app LLM boundaries.
- **`THIRD_PARTY.md`**: Open-source libraries and solver declarations.
- **`.env.example`**: Configuration template.

---

## ⚠️ Known Limitations
- The system currently focuses on the Monday–Friday teaching schedule and Monday–Saturday exam schedule; Sunday activities are reserved for emergency maintenance.
- Room capacity halving applies strictly to exams as mandated by the institutional guidelines.
