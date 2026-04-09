from fastapi import FastAPI
from pydantic import BaseModel
from groq import Groq
from supabase import create_client
import datetime
import os

# ================== CONFIG ==================
GROQ_API_KEY =  os.getenv("GROQ_API_KEY")
SUPABASE_URL = "https://dnhtssduplkosjdkpzbp.supabase.co"
SUPABASE_KEY = "sb_publishable_Z5lmGdco2JOfWFY304Hn3Q__Th8zb9O"

# Initialize clients
client = Groq(api_key=GROQ_API_KEY)
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI()

# ================== INPUT MODEL ==================
class UserInput(BaseModel):
    text: str

# ================== AI FUNCTION ==================
def extract_data(text):
    try:
        prompt = f"""
Extract amount, category, type (income/expense), and date from this:
{text}

Return ONLY in this format:
amount,category,type,date
Example:
300,petrol,expense,2026-04-09
"""

        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",   # ✅ working model
            messages=[{"role": "user", "content": prompt}]
        )

        result = response.choices[0].message.content.strip()
        print("AI RAW:", result)

        # Take last valid line
        lines = result.split("\n")
        result = lines[-1]

        parts = result.split(",")

        if len(parts) != 4:
            return None

        amount = parts[0].strip()
        category = parts[1].strip()
        type_ = parts[2].strip()
        date = parts[3].strip()

        # fallback date
        if date == "":
            date = str(datetime.date.today())

        return amount, category, type_, date

    except Exception as e:
        print("AI Error:", e)
        return None

# ================== ADD EXPENSE ==================
@app.post("/add-expense")
def add_expense(user_input: UserInput):
    data = extract_data(user_input.text)

    if not data:
        return {"error": "Failed to extract data"}

    amount, category, type_, date = data

    try:
        response = supabase.table("Expenses").insert({
            "Amount": int(amount),
            "Category": category,
            "Type": type_,
            "Date": date
        }).execute()

        return {
            "message": "Data added successfully",
            "data": {
                "Amount": amount,
                "Category": category,
                "Type": type_,
                "Date": date
            }
        }

    except Exception as e:
        return {"error": str(e)}

# ================== MONTHLY SUMMARY ==================
@app.get("/summary")
def get_summary(month: int, year: int):
    try:
        response = supabase.table("Expenses").select("*").execute()
        records = response.data

        total_income = 0
        total_expense = 0

        for row in records:
            date = datetime.datetime.strptime(row["Date"], "%Y-%m-%d")

            if date.month == month and date.year == year:
                if row["Type"].lower() == "income":
                    total_income += row["Amount"]
                else:
                    total_expense += row["Amount"]

        return {
            "month": month,
            "year": year,
            "total_income": total_income,
            "total_expense": total_expense,
            "savings": total_income - total_expense
        }

    except Exception as e:
        return {"error": str(e)}

# ================== ROOT ==================
@app.get("/")
def home():
    return {"message": "Finance API running 🚀"}




















