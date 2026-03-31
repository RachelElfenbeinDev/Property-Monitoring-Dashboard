# 🏠 Property Monitoring Dashboard
## 📍 LA City Housing Violation & Complaint Monitoring

## 📖 Project Overview
This project is a dedicated dashboard for automatically monitoring violation and complaint cases related to properties in Los Angeles, based on data collected from the **LA City Housing** website.

By entering a property identifier (**APN**), the system retrieves the relevant case list, enriches the data using each case’s detail page, stores the information in a local database, and presents a clear overview of the property’s current status.

The purpose of the system is to replace slow and repetitive manual tracking with a simple, practical, and efficient solution that allows the user to quickly identify:
- which cases are open
- what the latest status of each case is
- which issues require immediate attention

---

## 🔄 Workflow

### 1️⃣ APN Input
The user enters a 10-digit property identifier.

### 2️⃣ Data Extraction
The system performs scraping on the property’s main case listing page, retrieves the list of cases, and then accesses the relevant detail pages in order to enrich the data.

### 3️⃣ Storage and Comparison
The extracted data is stored in SQLite, while each new scrape is compared against the existing stored records.

### 4️⃣ Dashboard Presentation
The processed information is displayed in a clean and practical dashboard, making it easy to understand the current condition of the property and the urgency level of each case.

---

## ⚙️ Core System Logic

### 📥 1. Data Collection and Enrichment
The system extracts basic identifiers from the main results page, such as:
- `case_number`
- `case_type`
- `date_closed`

For active cases, the system also accesses the detail page in order to extract:
- `complaint_text`
- `events` – the full event timeline of the case

The latest status (`last_status`) is determined dynamically based on the most recent event in the event history.

---

### 👁️ 2. View State and Alert Logic (`is_viewed`)
To ensure that updates are not missed, the system manages a simple read/unread mechanism:

- **New case** → automatically marked as `not viewed`
- **Existing case with a changed status** → automatically marked as `not viewed`
- **Closed case** → automatically marked as `viewed`

This logic powers the dashboard badges and helps the user focus only on cases that actually require attention.

---

### 🚨 3. Priority Mapping Logic
The system translates raw regulatory statuses into clear business-oriented urgency levels:

| Example Status | Priority Level | Business Meaning |
|---|---|---|
| Order to Comply, Vacate Order | High | Immediate action is required to avoid penalties or escalation |
| Under Review, Hearing Scheduled | Medium | The case is in progress and should be monitored |
| Compliance Achieved, Dismissed | Low | The case has been resolved or no further action is needed |
| Other / Unknown | Unknown | A new or unclassified status that requires manual review |

---

### 🗂️ 4. Stored Fields and Why They Were Chosen
The system stores fields that serve two main purposes:
1. reflecting the property’s current condition at a given point in time
2. detecting changes across repeated scrapes

The main stored fields include:
- `apn` – property identifier
- `case_number` – case identifier
- `case_type` – case category
- `date_closed` – closing date, if available
- `complaint_text` – complaint description
- `last_status` – latest known case status
- `last_status_date` – date of the latest status
- `priority` – calculated urgency level
- `is_viewed` – whether the change of the case has already been reviewed by the user
- `scraped_at` – last scrape timestamp

### 💡 Why these fields
These fields provide the minimum necessary structure to:
- understand whether a case is open or closed
- identify the latest known status
- estimate urgency
- detect newly updated cases
- support a clear and practical dashboard without unnecessary clutter

---

## 🧠 How I Understood the Business Need
The business need was understood as the need for a simple tool that can monitor property-related case activity without requiring repeated manual checking of an external website.

Instead of requiring the user to:
- re-enter the APN again and again
- manually review the case list
- open each case one by one
- figure out alone what changed and what requires attention

the system centralizes the information into one place, preserves useful state between scrapes, and highlights the items that matter most for fast decision-making.

---

## 🧰 Tech Stack

### 🚀 MVP Stack
For the MVP version, I chose a lightweight and efficient stack that makes it possible to build a complete end-to-end solution quickly:

- **Language:** Python  
- **Backend Framework:** Flask  
- **Database:** SQLite  
- **Scraping Tools:** Requests + BeautifulSoup  
- **Frontend:** HTML / CSS / Bootstrap  

### ✅ Why this stack fits the MVP
- quick to set up and run
- easy to understand and maintain
- very suitable for a take-home assignment or proof of concept
- allows the effort to stay focused on business logic and data analysis rather than heavy infrastructure

---

## 🏗️ Production-Oriented Stack

If the system were to evolve into a full production or enterprise-grade product, the recommended stack would change according to scalability, reliability, and workload requirements.

### ⚡ Backend Framework
**FastAPI or Django**
- **FastAPI** is an excellent choice when natural asynchronous support, high performance, and modern API design are required under heavier workloads
- **Django** is an excellent choice when the system also needs built-in authentication, permissions, admin management, and a more opinionated full-stack structure

### 🗄️ Database
**PostgreSQL**
- stronger relational database than SQLite
- better suited for high concurrency
- better performance for more complex queries
- more appropriate for multi-user production environments

### 🔁 Distributed Task Queue
**A background task queue solution using Redis as a message broker**
- enables thousands of scraping jobs to run in parallel
- prevents the user interface from being blocked
- supports retries, scheduled refreshes, and large-scale monitoring workflows

### 🖥️ Frontend
**React or Vue.js**
- enables a fast, modern, and responsive SPA experience
- allows data updates without full page refresh
- significantly improves the user experience for ongoing monitoring scenarios

### ☁️ Infrastructure
**Docker + Kubernetes on AWS or GCP**
- enables clean and consistent deployment
- supports auto-scaling
- provides higher resilience, better service isolation, and enterprise-grade infrastructure management

---

## 🔮 Future Improvements

### ⚡ 1. Performance and Speed
- move to asynchronous processing
- send parallel requests

### 🧹 2. Duplicate Handling
- fix the existing issue in which multiple records may share the same `case_number` and `APN`
- define a more precise unique key per record

### 🧪 3. Testing Strategy
- add unit tests for parsing logic
- add integration tests for the full scraping pipeline
- add regression tests for critical business rules

---

## ▶️ Run Instructions

### 1️⃣ Install dependencies
```bash
pip install -r requirements.txt

### 2. Create and activate a virtual environment
```bash
python -m venv .venv
.venv\Scripts\activate
```

### 3. Run the server
```bash
python run.py
```

### 4. Open the application

Open the following URL in your browser:

http://127.0.0.1:5000

Then enter a valid APN.

---

### Summary

This project provides a practical, focused, and easy-to-use solution for monitoring property-related cases from the LA City Housing website.

For the MVP, I chose a lightweight and efficient stack that made it possible to build and demonstrate an end-to-end solution quickly.

For a future production-grade version, the architecture can be expanded into a more modern and scalable stack that supports large numbers of properties, users, concurrent scraping jobs, and enterprise-level operational requirements.
