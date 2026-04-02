from agno import Agent
from supabase import create_client
import google.generativeai as genai
import os

# Setup Gemini
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# Supabase setup
url = "https://dnhtssduplkosjdkpzbp.supabase.co"
key = "sb_publishable_Z5lmGdco2JOfWFY304Hn3Q__Th8zb9O"
supabase = create_client(url, key)

def add_expense(amount, category, type, date):
    supabase.table("Expenses").insert({
        "Amount": int(amount),
        "Category": category,
        "Type": type,
        "Date": date
    }).execute()
    
    return "Expense added successfully"

agent = Agent(
    name="Finance Agent",
    instructions="""
    Extract amount, category, type (income/expense), and date from user input.
    Then call add_expense function with those values.
    """
)

user_input = input("Enter your expense: ")
response = agent.run(user_input)

print("Agent Response:", response)

















