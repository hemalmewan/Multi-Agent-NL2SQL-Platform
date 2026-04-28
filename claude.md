# claude.md

## 🎯 Project Overview

Build a **professional medical-domain dashboard UI** called **Medicore**, using:

* **Frontend:** React (with modern UI libraries)
* **Backend Integration:** FastAPI (already implemented NL2SQL system)

The UI must be clean, modern, and aligned with **healthcare aesthetics** (light colors, calm tones, professional layout).

---

## 🧱 Tech Stack Requirements

### Frontend

* React (with Vite or Next.js preferred)
* Tailwind CSS (for styling)
* ShadCN UI / Material UI (for components)
* Plotly.js (for chart rendering)
* Axios (for API calls)
* React Router (navigation)
* Framer Motion (smooth animations)

### Backend

* FastAPI endpoints (already available)
* REST API integration

---

## 🎨 Design Guidelines

* Use **medical-themed colors**:

  * Primary: Blue (#2563EB)
  * Secondary: Teal (#14B8A6)
  * Background: Light Gray / White (#F8FAFC)
* Icons: Use healthcare icons (doctors, hospitals, charts)
* Keep UI **minimal, accessible, and professional**
* Add soft shadows, rounded cards, spacing

---

## 🧭 Navigation Bar

Top navigation bar must include:

* Home
* Medicore Dashboard
* Settings
* Help

Features:

* Sticky top navbar
* Logo on left (medical cross or heartbeat icon)
* Responsive design

---

## 🏠 Home Page

### Sections:

#### 1. Hero Section

* Title: “Medicore: AI-Powered Medical Data Insights”
* Subtitle: Explain NL2SQL in simple terms for **non-technical users**
* CTA Button: “Go to Dashboard”

#### 2. Product Overview

Explain:

* Converts natural language → SQL → charts
* Helps doctors, hospital admins, analysts

#### 3. Visual Icons Section

Include icons for:

* Doctors
* Nurses
* Patients
* Data analytics

#### 4. Features Section

* Ask questions in plain English
* Automatic chart generation
* Real-time insights

#### 5. Developer Info (Footer Section)

* Name: Hemal Mewantha
* Role: Final Year Data Science Undergraduate
* University: University of Colombo
* Add:

  * Photo (circular avatar)
  * Short bio
  * LinkedIn/GitHub icons

---

## 📊 Medicore Dashboard Page

### Layout:

#### 1. Pre-built Charts Section (Top)

Display 4 charts:

* Revenue Trends (Line Chart)
* Doctor Workload (Bar Chart)
* Top Diagnoses (Bar Chart)
* Payment Methods (Pie Chart)

Each chart must include:

* Title
* 2–3 sentence description
* Card-style container

---

#### 2. Chat + Query Section

Include:

* Chat input box
* Send button
* Message history (chat UI style)

Behavior:

* User enters query → API call → result returned

Display:

* Generated SQL (optional toggle)
* Chart visualization (Plotly)
* Table (if applicable)
* Text insight

---

#### 3. Result Display Area

Dynamic rendering:

* Chart (preferred)
* Table (fallback)
* Text summary

---

#### 4. Error & Alert Handling (VERY IMPORTANT)

##### Failed Query:

* Show alert banner:

  * “⚠️ Unable to process your query. Please try again.”

##### Ambiguous Query:

* Show modal popup:

  * Friendly message:
    “We need a bit more detail to help you better. Could you refine your query?”
* Input box for refined query

Style:

* Soft red/yellow tones
* Medical-friendly UI (not aggressive)

---

## ⚙️ Settings Page

Display analytics:

### Metrics:

* Token count (per query)
* Token cost
* Latency (ms)
* Total queries (runs)
* Total cost
* Average tokens

### UI:

* Use cards with icons:

  * ⏱️ Latency
  * 💰 Cost
  * 🔢 Tokens
  * 📊 Usage

### Additional:

* Charts for usage trends (optional)
* Medical-themed background

---

## ❓ Help Page

### Sections:

#### 1. System Architecture

* Visual diagram:

  * User → Router Agent → SQL Generator → DB → Result Interpreter
* Use icons for each component

---

#### 2. How to Use

Short steps:

1. Go to Dashboard
2. Enter query in plain English
3. View results

---

#### 3. Agent Descriptions

Explain briefly:

* Intent Router → identifies query type
* Ambiguity Checker → checks clarity
* Query Refiner → improves query
* SQL Generator → generates SQL
* Result Interpreter → creates charts & insights

---

## 📦 Additional Professional Enhancements

* Dark mode toggle
* Loading spinner during API calls
* Skeleton loaders for charts
* Export chart as PNG
* Download results as CSV
* Responsive design (mobile + tablet)
* Tooltip explanations for metrics
* Smooth transitions

---

## 🔗 API Integration

### Endpoint Example:

POST `/query`

Request:

```json
{
  "query": "Show revenue trends"
}
```

Response:

```json
{
  "status": "success",
  "sql_query": "...",
  "chart": {...},
  "table": [...],
  "insights": "...",
  "total_tokens": 120,
  "token_cost": 0.002,
  "latency_ms": 450
}
```

---

## 🧠 UX Principles

* Keep everything simple for non-technical users
* Always show feedback (loading, success, error)
* Avoid overwhelming UI
* Prioritize clarity over complexity

---

## ✅ Final Goal

Deliver a **production-level medical analytics dashboard** that:

* Feels professional
* Is easy to use
* Clearly explains AI outputs
* Handles errors gracefully
* Provides meaningful insights visually

---
