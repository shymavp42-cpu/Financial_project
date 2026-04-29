# tool.py

def add_expense(supabase, amount, category, type_, date):
    return supabase.table("Expenses").insert({
        "Amount": amount,
        "Category": category,
        "Type": type_.lower(),
        "Date": date
    }).execute()


def get_month_summary(supabase, month, year):
    response = supabase.table("Expenses").select("Amount,Type,Date").execute()
    records = response.data

    income = 0
    expense = 0

    for r in records:
        if not r.get("Date"):
            continue

        try:
            y, m, _ = map(int, r["Date"].split("-"))
        except:
            continue

        if y == year and m == month:
            if r["Type"].strip().lower() == "income":
                income += r["Amount"]
            elif r["Type"].strip().lower() == "expense":
                expense += r["Amount"]

    return income, expense


def get_balance(supabase):
    response = supabase.table("Expenses").select("Amount,Type").execute()
    records = response.data

    income = sum(r["Amount"] for r in records if r["Type"].lower() == "income")
    expense = sum(r["Amount"] for r in records if r["Type"].lower() == "expense")

    return income - expense