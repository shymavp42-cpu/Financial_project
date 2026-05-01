from fastapi import FastAPI
from supabase import create_client, Client
from groq import Groq
from dotenv import load_dotenv
import os
import json
import re
from datetime import datetime, timedelta

from tool import add_expense, get_month_summary, get_balance

load_dotenv()

app = FastAPI()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
client = Groq(api_key=GROQ_API_KEY)

conversation_history = []
pending_transaction = {}


# 🧠 MAIN LOGIC
def add_expense_logic(text):
    global conversation_history
    global pending_transaction

    try:
        text_lower = text.lower()

        # =========================================================
        # 🔥 EXPENSE DETECTION (UNCHANGED)
        # =========================================================
        expense_keywords = [
            "spent", "spend", "bought", "buy", "buying",
            "purchase", "purchased", "paid", "pay",
            "got", "received", "income", "salary"
        ]

        is_expense = any(word in text_lower for word in expense_keywords)

        # =========================================================
        # 📅 DATE HANDLING
        # =========================================================
        if "yesterday" in text_lower:
            target_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        else:
            target_date = datetime.now().strftime("%Y-%m-%d")

        # =========================================================
        # CASE 1: pending amount
        # =========================================================
        if pending_transaction and re.fullmatch(r"\d+", text.strip()):

            amount = int(text.strip())
            category = pending_transaction["category"]
            tx_type = pending_transaction["type"]
            date = pending_transaction.get("date", target_date)

            add_expense(
                supabase,
                amount,
                category,
                tx_type,
                date
            )

            pending_transaction = {}

            return f"✅ Added ₹{amount} for {category} on {date}"

        # =========================================================
        # CASE 2: EXPENSE FLOW (UNCHANGED LOGIC)
        # =========================================================
        if is_expense:

            amount_match = re.search(r"(?:₹|rs\.?|inr)?\s*(\d{2,})", text, re.IGNORECASE)

            if re.search(r"\d+\s*(kg|g|l|ml|km|m)", text_lower):
                pending_transaction = {
                    "type": "expense",
                    "category": "food",
                    "date": target_date
                }
                return "How much did it cost?"

            if amount_match is None:
                pending_transaction = {
                    "type": "expense",
                    "category": "others",
                    "date": target_date
                }
                return "How much did it cost?"

            amount = int(amount_match.group(1))

            tx_type = "income" if "salary" in text_lower or "income" in text_lower else "expense"

            add_expense(
                supabase,
                amount,
                "food",
                tx_type,
                target_date
            )

            return f"✅ Added ₹{amount} on {target_date}"

        # =========================================================
        # 📊 SUMMARY FIX (TODAY + MONTH + YEAR)
        # =========================================================
        if "summary" in text_lower:

            # =========================
            # 📍 TODAY SUMMARY (FIXED)
            # =========================
            if "today" in text_lower:

                today = datetime.now().strftime("%Y-%m-%d")

                response = supabase.table("Expenses").select("*").eq("Date", today).execute()
                records = response.data

                income = sum(r["Amount"] for r in records if r["Type"].lower() == "income")
                expense = sum(r["Amount"] for r in records if r["Type"].lower() == "expense")

                return (
                    f"📍 Today Summary\n"
                    f"💰 Income: ₹{income}\n"
                    f"💸 Expense: ₹{expense}\n"
                    f"📉 Balance: ₹{income - expense}"
                )

            # =========================
            # 📆 MONTH SUMMARY
            # =========================
            month_map = {
                "january": 1, "february": 2, "march": 3, "april": 4,
                "may": 5, "june": 6, "july": 7, "august": 8,
                "september": 9, "october": 10, "november": 11, "december": 12
            }

            month_num = None
            for m in month_map:
                if m in text_lower:
                    month_num = month_map[m]
                    break

            year_match = re.search(r"\b(20\d{2})\b", text_lower)
            year = int(year_match.group(1)) if year_match else datetime.now().year

            if month_num is not None:
                income, expense = get_month_summary(supabase, month_num, year)

                return (
                    f"📆 {text.strip()} Summary\n"
                    f"💰 Income: ₹{income}\n"
                    f"💸 Expense: ₹{expense}\n"
                    f"📉 Balance: ₹{income - expense}"
                )

            # =========================
            # 📊 YEAR SUMMARY
            # =========================
            response = supabase.table("Expenses").select("*").execute()
            records = response.data

            total_income = 0
            total_expense = 0

            for r in records:
                date_str = r.get("Date")
                if not date_str:
                    continue

                try:
                    date_obj = datetime.fromisoformat(date_str.replace("Z", ""))
                except:
                    continue

                if date_obj.year == year:
                    if r["Type"].lower() == "income":
                        total_income += r["Amount"]
                    elif r["Type"].lower() == "expense":
                        total_expense += r["Amount"]

            return (
                f"📊 {year} Summary\n"
                f"💰 Income: ₹{total_income}\n"
                f"💸 Expense: ₹{total_expense}\n"
                f"📉 Balance: ₹{total_income - total_expense}"
            )

        # =========================================================
        # 🤖 AI CHAT (SHORT ANSWER FIX)
        # =========================================================
        conversation_history.append({
            "role": "system",
            "content": "Keep responses short (3–5 lines max), clear and practical."
        })

        conversation_history.append({"role": "user", "content": text})

        if len(conversation_history) > 10:
            conversation_history = conversation_history[-10:]

        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=conversation_history,
            temperature=0.3
        )

        return response.choices[0].message.content

    except Exception as e:
        return f"❌ Error: {str(e)}"


# 🚀 API
@app.post("/chat")
def chat(data: dict):
    return {"response": add_expense_logic(data.get("text"))}