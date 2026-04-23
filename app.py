import os
import json
import uuid
from flask import Flask, render_template, request, redirect, url_for, send_file, session
import pandas as pd
from google import genai
from fpdf import FPDF
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.urandom(24)

# ── Gemini setup ────────────────────────────────────────────────────────────
GEMINI_API_KEY = "AIzaSyACQeZde8v-iP7CIKoPvsCCIHeNOy_Mkhg"
client = genai.Client(api_key=GEMINI_API_KEY)

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# ── Helpers ─────────────────────────────────────────────────────────────────

def parse_csv(filepath):
    df = pd.read_csv(filepath)
    df.columns = [c.strip() for c in df.columns]

    # Coerce numeric columns
    for col in ["Debit", "Credit", "Balance"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df = df.dropna(subset=["Date"])
    df = df.sort_values("Date")

    total_credits = df["Credit"].sum()
    total_debits = df["Debit"].sum()

    # Month-level stats
    df["YearMonth"] = df["Date"].dt.to_period("M")
    monthly_credits = df.groupby("YearMonth")["Credit"].sum()
    months = max(len(monthly_credits), 1)
    avg_credit = round(total_credits / months, 2)

    # Regular income: months where credit > 1000
    regular_income_months = (monthly_credits > 1000).sum()

    ratio = round(total_debits / total_credits, 2) if total_credits > 0 else 99

    start_balance = df["Balance"].iloc[0]
    end_balance = df["Balance"].iloc[-1]
    trend = "positive" if end_balance >= start_balance else "negative"

    summary = (
        f"Transactions: {len(df)} | Months: {months} | "
        f"Avg Monthly Credit: {avg_credit} | Debit/Credit Ratio: {ratio} | "
        f"Balance Trend: {trend} | Regular Income Months: {regular_income_months}/{months}"
    )
    
    metrics = {
        "total_credits": float(total_credits),
        "total_debits": float(total_debits),
        "months": months,
        "avg_credit": float(avg_credit),
        "regular_income_months": int(regular_income_months),
        "ratio": float(ratio),
        "trend": trend
    }
    return summary, metrics


def calculate_score(metrics):
    months = metrics["months"]
    regular_income_months = metrics["regular_income_months"]
    ratio = metrics["ratio"]
    trend = metrics["trend"]

    # 1. Income Regularity (0-25)
    # Proportion of months with regular income
    income_score = int((regular_income_months / months) * 25)
    income_score = max(5, min(25, income_score))

    # 2. Payment Discipline (0-25)
    # Based on Debit/Credit ratio
    if ratio < 0.7:
        payment_score = 24
    elif ratio < 0.9:
        payment_score = 20
    else:
        payment_score = 12
    # Add small variation if months are high
    if months >= 3: payment_score = min(25, payment_score + 1)

    # 3. Spending Stability (0-25)
    if ratio < 0.8:
        spending_score = 22
    elif ratio <= 1.0:
        spending_score = 18
    else:
        spending_score = 10
    
    # 4. Savings Behavior (0-25)
    if trend == "positive":
        savings_score = 23
    else:
        savings_score = 12

    # Final Total Score
    # Formula: 300 base + (sum of factors) * 6
    # Max: 300 + 100 * 6 = 900
    total_sum = income_score + payment_score + spending_score + savings_score
    total_score = 300 + (total_sum * 6)
    total_score = min(900, total_score)
    
    return {
        "total_score": int(total_score),
        "income_score": income_score,
        "payment_score": payment_score,
        "spending_score": spending_score,
        "savings_score": savings_score
    }


def call_gemini(summary, score):
    prompt = f"""You are a financial analyst. Based on this transaction summary and rule-based credit score, generate explanations and advice.

Transaction Summary: {summary}
Calculated Credit Score: {score}

Respond in this EXACT format, nothing else:
INCOME_TEXT: [exactly 2 sentences about income regularity]
PAYMENT_TEXT: [exactly 2 sentences about payment discipline and consistency]
SPENDING_TEXT: [exactly 2 sentences about spending habits and control]
SAVINGS_TEXT: [exactly 2 sentences about savings trend and balance]
SUMMARY: [exactly 3 sentences overall assessment and advice]"""

    try:
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=prompt,
        )
        if response and response.text:
            print(f"[FinScore] Gemini Raw Response:\n{response.text}")
            return response.text
        else:
            print("[FinScore] Gemini returned empty response.")
            return ""
    except Exception as e:
        print(f"[FinScore] Gemini API call failed: {e}")
        return ""


def parse_gemini_response(text):
    if not text:
        return {}
    result = {}
    allowed_keys = ["INCOME_TEXT", "PAYMENT_TEXT", "SPENDING_TEXT", "SAVINGS_TEXT", "SUMMARY"]
    for line in text.strip().splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            clean_key = key.strip().upper()
            if clean_key in allowed_keys:
                result[clean_key] = value.strip()
    return result


def score_color(score):
    score = int(score)
    if score < 550:
        return "#e53935"   # red
    if score < 700:
        return "#fb8c00"   # orange
    return "#2e7d32"       # green


def score_band(score):
    score = int(score)
    if score < 550:
        return "Poor"
    if score < 700:
        return "Fair"
    if score < 800:
        return "Good"
    return "Excellent"


# ── Routes ──────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/analyze", methods=["POST"])
def analyze():
    if "csv_file" not in request.files:
        return redirect(url_for("index"))

    file = request.files["csv_file"]
    if file.filename == "":
        return redirect(url_for("index"))

    # Save uploaded file
    filename = f"{uuid.uuid4().hex}.csv"
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)

    # ── Parse CSV ────────────────────────────────────────────────────────
    try:
        summary, metrics = parse_csv(filepath)
    except Exception as e:
        if os.path.exists(filepath):
            os.remove(filepath)
        return render_template("index.html", error=f"CSV parsing failed: {str(e)}.")
    finally:
        if os.path.exists(filepath):
            os.remove(filepath)

    # ── Calculate Scoring Locally ───────────────────────────────────────
    scores = calculate_score(metrics)
    
    # Base data for UI
    data = {
        "TOTAL_SCORE": str(scores["total_score"]),
        "INCOME_SCORE": str(scores["income_score"]),
        "PAYMENT_SCORE": str(scores["payment_score"]),
        "SPENDING_SCORE": str(scores["spending_score"]),
        "SAVINGS_SCORE": str(scores["savings_score"]),
    }

    # ── Call Gemini for Insights ─────────────────────────────────────────
    raw_text = call_gemini(summary, scores["total_score"])
    ai_insights = parse_gemini_response(raw_text)
    
    # Merge AI insights but PROTECT the scores from being overwritten
    for key in ["INCOME_TEXT", "PAYMENT_TEXT", "SPENDING_TEXT", "SAVINGS_TEXT", "SUMMARY"]:
        if key in ai_insights and ai_insights[key]:
            data[key] = ai_insights[key]

    # Ensure required keys exist with context-aware fallbacks
    if scores["total_score"] >= 700:
        defaults = {
            "INCOME_TEXT": "Income appears stable with consistent monthly credits observed in the transactions.",
            "PAYMENT_TEXT": "Payments are regular with no major irregularities or defaults observed in the statement.",
            "SPENDING_TEXT": "Spending is balanced, with essential expenses forming the baseline of debit activity.",
            "SAVINGS_TEXT": "Savings trend is healthy, showing a positive progression throughout the analyzed period.",
            "SUMMARY": "The user demonstrates stable financial behavior and consistent income patterns. Based on the transaction history, they are suitable for basic credit products and show a low-to-moderate risk profile.",
        }
    elif scores["total_score"] >= 550:
        defaults = {
            "INCOME_TEXT": "Income regularity is moderate, with some fluctuations in monthly credits.",
            "PAYMENT_TEXT": "Payment patterns are generally consistent but could be improved for better reliability.",
            "SPENDING_TEXT": "Spending shows moderate stability, with a few periods of higher-than-average debits.",
            "SAVINGS_TEXT": "Savings behavior is fair, though the balance trend shows some volatility.",
            "SUMMARY": "The user shows fair financial health with some areas for improvement in spending control. They may be eligible for limited credit products with additional verification.",
        }
    else:
        defaults = {
            "INCOME_TEXT": "Income regularity is low, with irregular or missing credit patterns observed.",
            "PAYMENT_TEXT": "Payment discipline shows significant irregularities that may impact creditworthiness.",
            "SPENDING_TEXT": "Spending levels are high relative to income, indicating potential liquidity constraints.",
            "SAVINGS_TEXT": "Savings trend is negative or stagnant, with ending balance lower than starting points.",
            "SUMMARY": "The user demonstrates high-risk financial behavior with irregular income and high spending. Significant improvements in savings and consistency are required for credit eligibility.",
        }
    for k, v in defaults.items():
        data.setdefault(k, v)

    data["color"] = score_color(data["TOTAL_SCORE"])
    data["band"] = score_band(data["TOTAL_SCORE"])
    data["generated_at"] = datetime.now().strftime("%d %B %Y, %I:%M %p")

    # Persist to temp JSON for PDF route
    result_id = uuid.uuid4().hex
    result_path = os.path.join(UPLOAD_FOLDER, f"{result_id}.json")
    with open(result_path, "w") as f:
        json.dump(data, f)

    session["result_id"] = result_id
    return render_template("result.html", data=data)


@app.route("/download")
def download():
    result_id = session.get("result_id")
    if not result_id:
        return redirect(url_for("index"))

    result_path = os.path.join(UPLOAD_FOLDER, f"{result_id}.json")
    if not os.path.exists(result_path):
        return redirect(url_for("index"))

    with open(result_path) as f:
        data = json.load(f)

    pdf_path = generate_pdf(data)
    return send_file(
        pdf_path,
        as_attachment=True,
        download_name="FinScore_Credit_Report.pdf",
        mimetype="application/pdf",
    )


# ── PDF Generation ──────────────────────────────────────────────────────────

def generate_pdf(data):
    class PDF(FPDF):
        def header(self):
            self.set_fill_color(22, 101, 52)   # dark green
            self.rect(0, 0, 210, 28, "F")
            self.set_font("Helvetica", "B", 18)
            self.set_text_color(255, 255, 255)
            self.set_y(8)
            self.cell(0, 12, "FinScore Credit Report", align="C")

        def footer(self):
            self.set_y(-15)
            self.set_font("Helvetica", "I", 8)
            self.set_text_color(120, 120, 120)
            self.cell(0, 10, "Generated by FinScore | Alternative Credit Assessment Platform", align="C")

    pdf = PDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=20)

    # Date
    pdf.set_y(35)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 8, f"Report Generated: {data.get('generated_at', datetime.now().strftime('%d %B %Y'))}", align="C")
    pdf.ln(10)

    # Score box
    score = data.get("TOTAL_SCORE", "650")
    band = data.get("band", "Good")
    color_map = {"Poor": (229, 57, 53), "Fair": (251, 140, 0), "Good": (46, 125, 50), "Excellent": (27, 94, 32)}
    r, g, b = color_map.get(band, (46, 125, 50))

    box_x, box_w, box_h = 70, 70, 44
    box_y = pdf.get_y()
    pdf.set_fill_color(r, g, b)
    pdf.set_draw_color(r, g, b)
    pdf.rect(box_x, box_y, box_w, box_h, "FD")

    # Score number centred inside box
    pdf.set_font("Helvetica", "B", 26)
    pdf.set_text_color(255, 255, 255)
    pdf.set_xy(box_x, box_y + 7)
    pdf.cell(box_w, 14, f"{score} / 900", align="C")

    # Band label below score number
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_xy(box_x, box_y + 23)
    pdf.cell(box_w, 12, band, align="C")

    # Advance cursor below score box
    pdf.set_y(box_y + box_h + 10)

    # Factor cards
    factors = [
        ("Income Regularity",   data.get("INCOME_SCORE", "0"),   data.get("INCOME_TEXT", "")),
        ("Payment Discipline",  data.get("PAYMENT_SCORE", "0"),  data.get("PAYMENT_TEXT", "")),
        ("Spending Stability",  data.get("SPENDING_SCORE", "0"), data.get("SPENDING_TEXT", "")),
        ("Savings Behavior",    data.get("SAVINGS_SCORE", "0"),  data.get("SAVINGS_TEXT", "")),
    ]

    for name, score_val, text in factors:
        # Measure text height first
        pdf.set_font("Helvetica", "", 10)
        text_lines = pdf.multi_cell(174, 6, text, split_only=True)
        text_h = len(text_lines) * 6
        card_h = 4 + 8 + text_h + 8   # pads + header row + text area

        # Robust Page Break Check: if card exceeds page bottom, add a new page
        if pdf.get_y() + card_h > 270:
            pdf.add_page()
            # No need to reset Y manually because add_page() and header() handle it, 
            # but we can adjust if header is large.
            # After add_page(), cursor is at top of page (below header margin)
            pdf.set_y(35) 

        card_y = pdf.get_y()
        pdf.set_fill_color(248, 253, 248)
        pdf.set_draw_color(200, 230, 200)
        pdf.rect(12, card_y, 186, card_h, "FD")

        # Header Row
        pdf.set_xy(16, card_y + 4)
        pdf.set_font("Helvetica", "B", 12)
        pdf.set_text_color(22, 101, 52)
        pdf.cell(120, 8, name)

        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(255, 255, 255)
        pdf.set_fill_color(22, 101, 52)
        pdf.cell(35, 7, f"{score_val} / 25", fill=True, align="C")

        # Text body
        pdf.set_xy(16, card_y + 13)
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(50, 50, 50)
        pdf.multi_cell(178, 6, text)

        pdf.set_y(card_y + card_h + 6)

    # Overall Summary
    summary_text = data.get("SUMMARY", "")
    pdf.set_font("Helvetica", "", 10)
    sum_lines = pdf.multi_cell(174, 6, summary_text, split_only=True)
    sum_h = 4 + 8 + (len(sum_lines) * 6) + 8

    if pdf.get_y() + sum_h > 270:
        pdf.add_page()
        pdf.set_y(35)

    sum_y = pdf.get_y()
    pdf.set_fill_color(237, 247, 237)
    pdf.set_draw_color(165, 214, 167)
    pdf.rect(12, sum_y, 186, sum_h, "FD")

    pdf.set_xy(16, sum_y + 4)
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(22, 101, 52)
    pdf.cell(0, 8, "Overall Assessment", ln=1)

    pdf.set_x(16)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(30, 30, 30)
    pdf.multi_cell(178, 6, summary_text)

    out_path = os.path.join(UPLOAD_FOLDER, f"report_{uuid.uuid4().hex}.pdf")
    pdf.output(out_path)
    return out_path


if __name__ == "__main__":
    app.run(debug=True, port=5051)
