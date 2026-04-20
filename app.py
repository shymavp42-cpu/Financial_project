from fastapi import FastAPI
from supabase import create_client, Client
from groq import Groq
from dotenv import load_dotenv
import os
from collections import defaultdict

# 🔐 Load .env
load_dotenv(dotenv_path=".env")

app = FastAPI()

# 🔐 ENV VARIABLES
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Debug (remove later)
print("SUPABASE_URL:", SUPABASE_URL)
print("SUPABASE_KEY:", SUPABASE_KEY)
print("GROQ_API_KEY:", GROQ_API_KEY)

# Clients
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
client = Groq(api_key=GROQ_API_KEY)


# 🧠 AI FUNCTION
def extract_data(text):
    prompt = f"""
You are a personal Finance Manager AI assistant.

Rules:
1. If greeting (hi, hello, hey):
   Return:
   CHAT: Hi! What are your expenses and income today?

2. If transaction:
   Return ONLY:
   amount,category,type,date

User input:
{text}
"""

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}]
    )

    result = response.choices[0].message.content.strip()

    # Take last line
    result = result.split("\n")[-1]

    if not result:
        return None

    return result


# ➕ ADD DATA
@app.post("/add")
def add_data(data: dict):
    user_input = data.get("text")

    extracted = extract_data(user_input)
    print("AI OUTPUT:", extracted)

    # 🔴 If nothing returned
    if not extracted:
        return {
            "message": "Hi! What are your expenses or income today?"
        }

    # 💬 CHAT RESPONSE
    # If AI didn't return transaction format
    if "," not in extracted:
        return {
            "message": extracted.replace("CHAT:", "").strip()
        }

    # 💰 TRANSACTION RESPONSE
    try:
        parts = extracted.split(",")

        # 🔴 Safety check (must be exactly 4 values)
        if len(parts) != 4:
            return {
                "message": "Please enter like: I spent 200 on food"
            }

        amount, category, type_, date = parts

        supabase.table("Expenses").insert({
            "Amount": int(amount),
            "Category": category.strip(),
            "Type": type_.strip(),
            "Date": date.strip()
        }).execute()

        return {
            "message": f"Added: ₹{amount} for {category}"
        }

    except Exception as e:
        print("ERROR:", e)
        return {
            "message": "Please enter like: I spent 200 on food"
        }
# 📊 MONTHLY SUMMARY
@app.get("/summary")
def monthly_summary(month: int, year: int):
    try:
        response = supabase.table("Expenses").select("*").execute()
        records = response.data

        total_income = 0
        total_expense = 0

        for r in records:
            if not r.get("Date"):
                continue

            date = r["Date"]
            y, m, _ = map(int, date.split("-"))

            if y == year and m == month:
                if r["Type"] == "income":
                    total_income += r["Amount"]
                elif r["Type"] == "expense":
                    total_expense += r["Amount"]

        return {
            "month": month,
            "year": year,
            "total_income": total_income,
            "total_expense": total_expense,
            "balance": total_income - total_expense
        }

    except Exception as e:
        return {"error": str(e)}


# 📊 CATEGORY-WISE SUMMARY
@app.get("/category-summary")
def category_summary(month: int, year: int):
    try:
        response = supabase.table("Expenses").select("*").execute()
        records = response.data

        category_totals = defaultdict(int)

        for r in records:
            if not r.get("Date"):
                continue

            date = r["Date"]
            y, m, _ = map(int, date.split("-"))

            if y == year and m == month and r["Type"] == "expense":
                category_totals[r["Category"]] += r["Amount"]

        return dict(category_totals)

    except Exception as e:
        return {"error": str(e)}


# 🔍 TEST API
@app.get("/test")
def test():
    try:
        response = supabase.table("Expenses").select("*").execute()
        return response.data
    except Exception as e:
        return {"error": str(e)}


def add_expense_logic(text):
    extracted = extract_data(text)
    print("AI OUTPUT:", extracted)

    # 🔴 If nothing
    if not extracted:
        return "Hi! What are your expenses or income today?"

    # 💬 CHAT RESPONSE
    if "," not in extracted:
        return extracted.replace("CHAT:", "").strip()

    # 💰 TRANSACTION
    try:
        parts = extracted.split(",")

        if len(parts) != 4:
            return "Please enter like: I spent 200 on food"

        amount, category, type_, date = parts

        supabase.table("Expenses").insert({
            "Amount": int(amount),
            "Category": category.strip(),
            "Type": type_.strip(),
            "Date": date.strip()
        }).execute()

        return f"✅ {type_.capitalize()} of ₹{amount} added under {category}"

    except Exception as e:
        return f"❌ Error: {str(e)}"


def get_all_data():
    response = supabase.table("Expenses").select("*").execute()
    return response.data


def get_monthly_summary(month, year):
    response = supabase.table("Expenses").select("*").execute()
    records = response.data

    total_income = 0
    total_expense = 0

    for r in records:
        if not r.get("Date"):
            continue

        y, m, _ = map(int, r["Date"].split("-"))

        if y == int(year) and m == int(month):
            if r["Type"] == "income":
                total_income += r["Amount"]
            elif r["Type"] == "expense":
                total_expense += r["Amount"]

    return {
        "income": total_income,
        "expense": total_expense
    }

def get_yearly_summary(year):
    response = supabase.table("Expenses").select("*").execute()
    records = response.data

    monthly_income = {}
    monthly_expense = {}

    for r in records:
        if not r.get("Date"):
            continue

        y, m, _ = map(int, r["Date"].split("-"))

        if y == int(year):
            if r["Type"].lower() == "income":
                monthly_income[m] = monthly_income.get(m, 0) + r["Amount"]
            elif r["Type"].lower() == "expense":
                monthly_expense[m] = monthly_expense.get(m, 0) + r["Amount"]

    return monthly_income, monthly_expense



