# 🏦 FinScore — 🇮🇳 Financial Inclusion via logic

> **Bridging the Credit Gap for 190M+ Unbanked Indians**  
> FinScore is a hybrid alternative credit assessment platform that analyzes UPI / bank statement CSVs to generate a professional credit report for users without formal credit history.

---

## 🚀 The Mission
Over **190 million Indians** earn consistently through UPI but lack a formal "CIBIL Score," making them ineligible for traditional loans. **FinScore** bridges this gap by transforming transaction metadata into a high-trust alternative credit score powered by **Google Gemini 1.5 Flash**.

---

## ✨ Key Features
- 📊 **Intelligent Analysis**: Automatically parses CSV transaction logs to identify earning patterns.
- 🧠 **AI-Powered Insights**: Uses Gemini 1.5 Flash to provide human-like qualitative assessments of financial health.
- 🎨 **Dynamic Dashboard**: A premium, green-themed UI featuring animated score rings and interactive factor cards.
- 📄 **Professional PDF Export**: One-click download of a structured and readable PDF report.
- 🔒 **Privacy First**: Fully stateless design. Data is processed in real-time and never stored permanently.

---

## 🛠️ Tech Stack
| Component | Technology |
| :--- | :--- |
| **Backend** | Python 3.9+ / Flask |
| **Generative AI** | Google Gemini 1.5 Flash API |
| **Data Engine** | Pandas (Time-series & statistical analysis) |
| **Report Engine** | fpdf2 (Dynamic Layout Engine) |
| **Frontend** | HTML5, Vanilla CSS (Custom Design System) |

---

## 🧠 How It Works (The Hybrid Engine)

FinScore uses a **Hybrid Scoring System** that combines deterministic rule-based algorithms with AI-generated qualitative insights.

### 1. Data Engineering (Pandas)
The engine parses raw CSV logs and extracts structured metrics:
- **Income Regularity**: Proportion of months where credits exceed ₹1,000.
- **Payment Discipline**: Analysis of Debit-to-Credit velocity and consistency.
- **Spending Stability**: Multi-tier assessment of liquidity and expense control.
- **Savings Behavior**: Historical balance trend analysis.

### 2. Rule-Based Scoring (Python Backend)
Unlike systems that rely solely on AI, FinScore calculates the **Credit Score (300-900)** and **Factor Scores (0-25)** locally in Python. This ensures:
- **Consistency**: The same data always results in the same score.
- **Transparency**: Clear mathematical logic behind every point awarded.
- **Reliability**: A functional score is generated even if the API is offline.

### 3. AI Insights (Gemini 1.5 Flash)
Once the score is calculated, the metrics are sent to Gemini to generate human-readable explanations, financial advice, and risk summaries. If the API fails, a context-aware fallback system provides high-quality static assessments tailored to the user's score range.

---

## 📥 Getting Started

### 1. Prerequisite: Gemini API Key
Generate a free API key at [Google AI Studio](https://aistudio.google.com/).

### 2. Installation
```bash
python3 -m pip install -r requirements.txt
```

### 3. Run the App
```bash
python3 app.py
```
Open **[http://localhost:5051](http://localhost:5051)** in your browser.

---

## 📊 Score Bands
| Range | Band | Visual Indicator |
| :--- | :--- | :--- |
| **300–549** | Poor | 🔴 High Risk |
| **550–699** | Fair | 🟠 Moderate Risk |
| **700–799** | Good | 🟢 Healthy |
| **800–900** | Excellent | 🟢 Prime |

---

## 🤝 Team & Credit
**Developed by:** Gouseraza  
**Hackathon:** First Hackathon 2026

---

## 📸 Screenshots

### Home Page
![Home](screenshots/home.png)

### Result Dashboard
![Result](screenshots/result.png)

- 📈 **Dynamic Behavior Testing**: The system adapts scores based on different transaction patterns (low, mid, high financial profiles).