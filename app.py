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

# 🛠️ TOOL DEFINITIONS FOR GROQ
tools = [
    {
        "type": "function",
        "function": {
            "name": "add_expense",
            "description": "ONLY call this when you have the amount, category, type, and date. If any info is missing, talk to the user instead.",
            "parameters": {
                "type": "object",
                "properties": {
                    "amount": {"type": "number", "description": "The exact amount of money."},
                    "category": {"type": "string", "description": "Category (e.g., food, travel, salary)."},
                    "type": {"type": "string", "enum": ["income", "expense"], "description": "Whether it is income or an expense."},
                    "date": {"type": "string", "description": "The date in YYYY-MM-DD format."}
                },
                "required": ["category", "type", "date"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_month_summary",
            "description": "Get the financial summary for a specific month.",
            "parameters": {
                "type": "object",
                "properties": {
                    "month": {"type": "integer", "description": "Month (1-12)."},
                    "year": {"type": "integer", "description": "Year (e.g., 2024)."}
                },
                "required": ["month", "year"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_balance",
            "description": "Get the total current balance.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    }
]

# In-memory storage for conversation history
conversation_history = []

# 🧠 AI AGENT (LLM DECISION MAKER)
def add_expense_logic(text):
    global conversation_history
    try:
        print("STEP 1: received input")
        current_date = datetime.now().strftime("%Y-%m-%d")

        system_prompt = {
            "role": "system",
            "content": (
                "### ROLE\n"
                "You are an expert Personal Finance AI Assistant. Your goal is to help users track their money with precision and minimal friction.\n\n"
                "### CAPABILITIES\n"
                "- Log expenses and income.\n"
                "- Provide monthly summaries and current balances.\n"
                "- Infer categories (e.g., 'apples' -> food, 'uber' -> transport).\n"
                "- Perform calculations (e.g., '3kg at 50/kg' -> 150).\n\n"
                "### STRICT GUIDELINES\n"
                "1. *Validation*: NEVER call a tool if the 'amount' is unknown. If the user mentions an item but not a price, ask for it immediately.\n"
                "2. *Date Defaulting*: Assume all transactions happened 'today' (%s) unless a specific date/relative time is provided.\n"
                "3. *Tone*: Be professional, helpful, and extremely concise. Avoid long introductory text.\n"
                "4. *Memory*: Use the conversation history to resolve references (e.g., 'it cost 50' refers to the previous item)." % current_date
            )
        }

        # Append user message to history
        conversation_history.append({"role": "user", "content": text})

        # Keep history manageable (e.g., last 10 messages)
        if len(conversation_history) > 10:
            conversation_history = conversation_history[-10:]

        # Prepare messages for the LLM
        messages = [system_prompt] + conversation_history

        print("STEP 2: calling LLM with tools and memory")
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=messages,
            tools=tools,
            tool_choice="auto",
            temperature=0
        )

        response_message = response.choices[0].message
        tool_calls = response_message.tool_calls

        # Add assistant's response to history (as a dict for stability)
        history_entry = {
            "role": "assistant",
            "content": response_message.content
        }
        if tool_calls:
            history_entry["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments
                    }
                } for tc in tool_calls
            ]
        
        conversation_history.append(history_entry)

        if not tool_calls:
            return response_message.content

        print("STEP 3: tool calls detected")
        for tool_call in tool_calls:
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)

            print(f"STEP 4: executing tool: {function_name}")
            
            tool_result = ""
            if function_name == "add_expense":
                amount = function_args.get("amount")

                import re
                numbers_in_text = re.findall(r'\d+', text)

# Convert all numbers from text to integers
                numbers_in_text = [int(n) for n in numbers_in_text]

# 🔴 Case 1: No number at all
                if not numbers_in_text:
                    return "How much did it cost?"

# 🔴 Case 2: Only small numbers (like 1kg, 2 items) → NOT a price
                if all(n <= 10 for n in numbers_in_text):
                    return "How much did it cost?"

# 🔴 Case 3: Invalid amount from model
                if amount is None or amount <= 0:
                    return "Please enter the exact amount (e.g., 'I bought apples for 120')"

# ✅ Save data
                add_expense(
                    supabase,
                    amount,
                    function_args["category"],
                    function_args["type"],
                    function_args["date"]
)

                tool_result = f"✅ Added ₹{amount} for {function_args['category']}."
            elif function_name == "get_month_summary":
                income, expense = get_month_summary(
                    supabase,
                    function_args["month"],
                    function_args["year"]
                )
                tool_result = f"📊 {function_args['month']}/{function_args['year']}: +₹{income} | -₹{expense} | Bal: ₹{income-expense}"

            elif function_name == "get_balance":
                balance = get_balance(supabase)
                tool_result = f"🏦 Total Balance: ₹{balance}"

            # Add tool result to history
            conversation_history.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "name": function_name,
                "content": tool_result
            })
            
            return tool_result

        return "❌ I encountered an issue while processing your request."

    except Exception as e:
        print("ERROR:", e)
        return f"❌ Error: {str(e)}"

# 🚀 CHAT API
@app.post("/chat")
def chat(data: dict):
    return {"response": add_expense_logic(data.get("text"))}

# 🧹 CLEAR HISTORY API
@app.post("/clear")
def clear_history():
    global conversation_history
    conversation_history = []
    return {"message": "Chat history cleared"}

# 🔍 TEST API
@app.get("/test")
def test():
    try:
        # Fetching only necessary columns and limiting for safety
        response = supabase.table("Expenses").select("*").limit(100).execute()
        return response.data
    except Exception as e:
        return {"error": str(e)}

# 📊 MONTHLY SUMMARY API (for graphs)
@app.get("/summary")
def summary(month: int, year: int):
    try:
        # Optimization: Filter in DB instead of Python
        income, expense = get_month_summary(supabase, month, year)
        return {
            "total_income": income,
            "total_expense": expense,
            "balance": income - expense
        }
    except Exception as e:
        return {"error": str(e)}