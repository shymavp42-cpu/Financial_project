from fastapi import FastAPI
from supabase import create_client, Client
from groq import Groq
from dotenv import load_dotenv
import os
import json
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


# 🧠 AI AGENT (LLM DECISION MAKER)
def add_expense_logic(text):
    try:
        print("STEP 1: received input")

        # 🧠 STRICT PROMPT (VERY IMPORTANT)
        prompt = f"""
You are a strict JSON generator for a finance AI system.

You MUST return ONLY valid JSON. No explanations.

Available tools:
1. add_expense → requires amount, category, type (income/expense), date (YYYY-MM-DD)
2. get_month_summary → requires month (1-12), year
3. get_balance → no parameters

Rules:
- Output ONLY JSON
- No markdown
- No extra text

Example:
{{
  "tool": "add_expense",
  "parameters": {{
    "amount": 200,
    "category": "food",
    "type": "expense",
    "date": "2026-03-15"
  }}
}}

User:
{text}
"""

        print("STEP 2: calling LLM")

        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )

        result = response.choices[0].message.content.strip()

        print("STEP 3: LLM responded")
        print("RAW OUTPUT:", result)

        # 🧠 SAFE JSON PARSING
        try:
            action = json.loads(result)
        except json.JSONDecodeError:
            print("❌ Invalid JSON from LLM")
            return "❌ AI returned invalid response"

        print("STEP 4: JSON parsed")

        tool = action.get("tool")
        params = action.get("parameters", {})

        print("STEP 5: executing tool:", tool)

        # 🛠 TOOL: ADD EXPENSE
        if tool == "add_expense":

            required = ["amount", "category", "type", "date"]
            if not all(k in params for k in required):
                return "❌ Missing fields from AI"

            supabase.table("Expenses").insert({
                "Amount": params["amount"],
                "Category": params["category"],
                "Type": params["type"].strip().lower(),
                "Date": params["date"]
            }).execute()

            return f"✅ Added {params['type']} ₹{params['amount']}"

        # 📊 TOOL: MONTH SUMMARY
        elif tool == "get_month_summary":

            income, expense = get_month_summary(
                supabase,
                params["month"],
                params["year"]
            )

            return (
                f"📊 Monthly Summary\n"
                f"💰 Income: ₹{income}\n"
                f"💸 Expense: ₹{expense}\n"
                f"📉 Balance: ₹{income - expense}"
            )

        # 🏦 TOOL: BALANCE
        elif tool == "get_balance":
            balance = get_balance(supabase)
            return f"🏦 Total Balance: ₹{balance}"

        return "❌ Unknown tool requested"

    except Exception as e:
        print("ERROR:", e)
        return f"❌ Error: {str(e)}"

# 🚀 CHAT API (Gradio calls this)
@app.post("/chat")
def chat(data: dict):
    return {"response": add_expense_logic(data.get("text"))}


# 🔍 TEST API
@app.get("/test")
def test():
    try:
        response = supabase.table("Expenses").select("*").execute()
        return response.data
    except Exception as e:
        return {"error": str(e)}


# 📊 MONTHLY SUMMARY API (for graphs)
@app.get("/summary")
def summary(month: int, year: int):
    try:
        response = supabase.table("Expenses").select("*").execute()
        records = response.data

        income = 0
        expense = 0

        for r in records:
            date_str = r.get("Date")

            if not date_str:
                continue

            try:
                # ✅ safe parsing
                y, m, d = map(int, str(date_str).split("-"))
            except:
                continue

            if y == year and m == month:
                r_type = r.get("Type", "").strip().lower()
                amount = r.get("Amount", 0)

                if r_type == "income":
                    income += amount
                elif r_type == "expense":
                    expense += amount

        return {
            "total_income": income,
            "total_expense": expense,
            "balance": income - expense
        }

    except Exception as e:
        return {"error": str(e)}