# 🖥️ System Monitoring & IT Asset Management Platform

A full-stack web application that monitors live system health (CPU, RAM,
Disk, Network) in real time and manages an organization's IT asset
inventory — with automatic threshold-based alerting. Built with **Flask**,
**SQLite**, vanilla **JavaScript**, and **Chart.js**.

**Author:** Aditya Kumar
**Email:** agile.aditya.kumar@gmail.com

---

## ✨ Features

- **Real-Time System Monitoring** — live CPU, RAM, Disk, Network and uptime
  stats, refreshed every 3 seconds and plotted on a live line chart.
- **Automated Alerting** — auto-generates and logs alerts whenever CPU,
  RAM, or Disk usage crosses configurable thresholds (80% / 80% / 90%).
- **IT Asset Management (CRUD)** — add, edit, delete, and track hardware
  assets (laptops, desktops, servers, printers, routers) with owner,
  status, location, and purchase date.
- **Dashboard Summary** — at-a-glance counts of total/active/maintenance
  assets and total alerts raised.
- **Clean, Responsive UI** — dark-themed dashboard built with plain
  HTML/CSS/JS, no frontend framework required.

## 🧱 Tech Stack

| Layer      | Technology                     |
|------------|---------------------------------|
| Backend    | Python, Flask                  |
| Database   | SQLite                         |
| Monitoring | psutil                         |
| Frontend   | HTML5, CSS3, JavaScript, Chart.js |

## 📂 Project Structure

```
itam-platform/
├── app.py                 # Flask backend (routes + APIs)
├── requirements.txt       # Python dependencies
├── templates/
│   └── index.html         # Dashboard UI
├── static/
│   ├── style.css          # Styling
│   └── script.js          # Frontend logic (fetch, charts, CRUD)
└── README.md
```

## 🚀 Getting Started

### 1. Clone the repository
```bash
git clone https://github.com/<your-username>/itam-platform.git
cd itam-platform
```

### 2. Create a virtual environment (recommended)
```bash
python -m venv venv
source venv/bin/activate      # On Windows: venv\Scripts\activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Run the app
```bash
python app.py
```

The app will start at **http://127.0.0.1:5000/** — open it in your browser.

## 🔌 API Endpoints

| Method | Endpoint              | Description                  |
|--------|------------------------|-------------------------------|
| GET    | `/api/system-stats`    | Live CPU/RAM/Disk/Network data |
| GET    | `/api/summary`         | Dashboard summary counts      |
| GET    | `/api/alerts`          | Last 20 system alerts         |
| GET    | `/api/assets`          | List all IT assets            |
| POST   | `/api/assets`          | Add a new asset               |
| PUT    | `/api/assets/<id>`     | Update an existing asset      |
| DELETE | `/api/assets/<id>`     | Delete an asset                |

## 🗺️ Possible Enhancements

- User authentication & role-based access
- Email/Slack notifications for critical alerts
- Historical usage reports (daily/weekly graphs)
- Multi-server monitoring via agents
- Export asset inventory to CSV/Excel

## 📄 License

This project is open-source and free to use for learning purposes.

---
Made with ❤️ by **Aditya Kumar**
