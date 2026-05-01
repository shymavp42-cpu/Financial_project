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
pending_transaction = {}

# =========================
# 🔥 ONLY FIXED PART
# =========================
def detect_category(text_lower):

    # 🍎 FOOD (expanded for real usage)
    food_keywords = [
        "apple", "apples", "food", "rice", "meal", "milk",
        "banana", "bread", "snack", "lunch", "dinner",
        "juice", "tea", "coffee", "fruit",
        "oil", "ghee", "butter", "vegetable", "vegetables", "cook"
    ]

    # 🚗 TRANSPORT
    transport_keywords = [
        "auto", "uber", "ola", "bus", "train", "petrol",
        "fuel", "taxi", "travel", "ride", "fare"
    ]

    # 💰 INCOME
    income_keywords = [
        "salary", "income", "got", "received", "credited"
    ]

    # 🔥 IMPORTANT FIX: ensure "1L oil", "2kg rice" still work
    if any(word in text_lower for word in food_keywords):
        return "food"
    elif any(word in text_lower for word in transport_keywords):
        return "transport"
    elif any(word in text_lower for word in income_keywords):
        return "salary"
    else:
        return "others"


# 🧠 MAIN LOGIC
def add_expense_logic(text):
    global conversation_history
    global pending_transaction

    try:
        current_date = datetime.now().strftime("%Y-%m-%d")

        system_prompt = {
            "role": "system",
            "content": "You are a finance AI assistant"
        }

        if "balance" in text.lower():
            return "⚠️ That is a balance, not a transaction."

        text_lower = text.lower()

        # =========================
        # 🔥 CASE 1: pending amount
        # =========================
        if pending_transaction and re.fullmatch(r"\d+", text.strip()):

            amount = int(text.strip())
            category = pending_transaction["category"]
            tx_type = pending_transaction["type"]

            add_expense(
                supabase,
                amount,
                category,
                tx_type,
                datetime.now().strftime("%Y-%m-%d")
            )

            pending_transaction = {}

            return f"✅ Added ₹{amount} for {category}"

        # =========================
        # 🔥 CASE 2: new message
        # =========================
        if any(word in text_lower for word in ["spent", "bought", "paid", "salary", "income", "got"]):

            # ✅ FIXED CATEGORY LOGIC
            category = detect_category(text_lower)

            if re.search(r"\d+\s*(kg|g|l|ml|km|m)", text_lower):
                pending_transaction = {"type": "expense", "category": category}
                return "How much did it cost?"

            amount_match = re.search(r"(?:₹|rs\.?|inr)?\s*(\d{2,})", text, re.IGNORECASE)

            if amount_match is None:
                pending_transaction = {"type": "expense", "category": category}
                return "How much did it cost?"

            amount = int(amount_match.group(1))

            tx_type = "income" if any(word in text_lower for word in ["salary", "income", "got"]) else "expense"

            add_expense(
                supabase,
                amount,
                category,
                tx_type,
                datetime.now().strftime("%Y-%m-%d")
            )

            return f"✅ Added ₹{amount} as {tx_type} ({category})"

        # =========================
        # LLM (UNCHANGED)
        # =========================
        conversation_history.append({"role": "user", "content": text})

        if len(conversation_history) > 10:
            conversation_history = conversation_history[-10:]

        messages = [system_prompt] + conversation_history

        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=messages,
            temperature=0.7
        )

        return response.choices[0].message.content

    except Exception as e:
        return f"❌ Error: {str(e)}"


# 🚀 API (UNCHANGED)
@app.post("/chat")
def chat(data: dict):
    return {"response": add_expense_logic(data.get("text"))}


@app.post("/clear")
def clear():
    global conversation_history
    conversation_history = []
    return {"message": "cleared"}


@app.get("/test")
def test():
    return supabase.table("Expenses").select("*").execute().data


@app.get("/summary")
def summary(month: int, year: int):
    income, expense = get_month_summary(supabase, month, year)
    return {
        "total_income": income,
        "total_expense": expense,
        "balance": expense - income
    }