from fastapi import FastAPI
from supabase import create_client, Client
from groq import Groq
from dotenv import load_dotenv
import os
import json
import re
from datetime import datetime

from tool import add_expense, get_month_summary, get_balance

# 🔐 Load environment variables
load_dotenv()

app = FastAPI()

# 🔐 ENV VARIABLES
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Clients
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
client = Groq(api_key=GROQ_API_KEY)

conversation_history = []

# 🧠 MAIN LOGIC
def add_expense_logic(text):
    global conversation_history

    try:
        current_date = datetime.now().strftime("%Y-%m-%d")

        # ✅ YOUR PROMPT (unchanged style)
        system_prompt = {
            "role": "system",
            "content": (
                "### ROLE\n"
                "You are an expert Personal Finance AI Assistant.\n\n"
                "### CAPABILITIES\n"
                "- Log expenses and income.\n"
                "- Provide summaries and balances.\n"
                "- Infer categories.\n\n"
                "### STRICT GUIDELINES\n"
                "1. *Validation*: NEVER call a tool if amount is unknown.\n"
                "2. *Date Defaulting*: Assume today (%s).\n"
                "3. *Tone*: Be concise.\n"
                "4. *Memory*: Use conversation history.\n"
                "5. If user asks advice or analysis, DO NOT call tools.\n"
                "6. If user asks yearly summary, DO NOT call monthly tool.\n"
                % current_date
            )
        }

        # 🚫 prevent wrong saving
        if "balance" in text.lower():
            return "⚠️ That is a balance, not a transaction."

        # =========================================================
        # 🔥 YEAR SUMMARY (FINAL FIX — ONLY ONE BLOCK)
        # =========================================================
        year_match = re.search(r"\b(20\d{2})\b", text)

        if "summary" in text.lower() and ("year" in text.lower() or year_match):

            if "this year" in text.lower():
                year = datetime.now().year
            elif year_match:
                year = int(year_match.group(1))
            else:
                year = None

            if year is not None:
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
                        y = date_obj.year
                    except:
                        continue

                    if y == year:
                        if r["Type"].lower() == "income":
                            total_income += r["Amount"]
                        elif r["Type"].lower() == "expense":
                            total_expense += r["Amount"]

                if total_income == 0 and total_expense == 0:
                    return f"⚠️ No data found for {year}"

                return f"📊 {year} Summary: +₹{total_income} | -₹{total_expense} | Balance ₹{total_income - total_expense}"

        # =========================================================
        # 🔥 CATEGORY ADVICE
        # =========================================================
        if "category" in text.lower() and ("reduce" in text.lower() or "limit" in text.lower()):
            response = supabase.table("Expenses").select("*").execute()
            records = response.data

            category_totals = {}

            for r in records:
                if r["Type"].lower() == "expense":
                    cat = r["Category"]
                    category_totals[cat] = category_totals.get(cat, 0) + r["Amount"]

            if not category_totals:
                return "No expense data available."

            highest = max(category_totals, key=category_totals.get)
            return f"💡 You are spending the most on '{highest}'. Try reducing this category."

        # =========================================================
        # 🤖 LLM PART (unchanged logic)
        # =========================================================
        conversation_history.append({"role": "user", "content": text})

        if len(conversation_history) > 10:
            conversation_history = conversation_history[-10:]

        messages = [system_prompt] + conversation_history

        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=messages,
            temperature=0
        )

        return response.choices[0].message.content

    except Exception as e:
        return f"❌ Error: {str(e)}"


# 🚀 CHAT API
@app.post("/chat")
def chat(data: dict):
    return {"response": add_expense_logic(data.get("text"))}


# 🧹 CLEAR
@app.post("/clear")
def clear():
    global conversation_history
    conversation_history = []
    return {"message": "cleared"}


# 🔍 TEST
@app.get("/test")
def test():
    return supabase.table("Expenses").select("*").execute().data


# 📊 MONTH SUMMARY (API)
@app.get("/summary")
def summary(month: int, year: int):
    income, expense = get_month_summary(supabase, month, year)
    return {
        "total_income": income,
        "total_expense": expense,
        "balance": income - expense
    }