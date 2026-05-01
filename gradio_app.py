import gradio as gr
import pandas as pd
import matplotlib.pyplot as plt
import requests
import logging

# 🔐 Logging
logging.basicConfig(
    filename="app.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

BASE_URL = "http://127.0.0.1:8000"

logging.info("🚀 Gradio App Started")


# 💬 CHAT FUNCTION (backend call)
def chat_fn(message):
    logging.info(f"Chat input: {message}")
    try:
        res = requests.post(
            f"{BASE_URL}/chat",
            json={"text": message}
        )

        data = res.json()
        response = data.get("response", "No response")

        # ✅ Remove unwanted quotes
        if isinstance(response, str):
            response = response.strip('"').strip("'")

        logging.info(f"Response: {response}")

        return response, ""   # ✅ clears input box

    except Exception as e:
        logging.error(f"Chat error: {e}")
        return "❌ Error connecting to backend", ""


# 💬 CHAT UI HANDLER (kept as it is)
def chat_ui(message, history):
    response = chat_fn(message)

    history.append({"role": "user", "content": message})
    history.append({"role": "assistant", "content": response})

    return history, ""


# 📋 ADMIN DATA
def admin_fn():
    logging.info("Fetching admin data")
    try:
        res = requests.get(f"{BASE_URL}/test")
        data = res.json()
        return pd.DataFrame(data)

    except Exception as e:
        logging.error(f"Admin error: {e}")
        return pd.DataFrame()


# 📊 MONTHLY GRAPH
def monthly_graph_fn(month, year):
    logging.info(f"Monthly graph for {month}-{year}")

    try:
        res = requests.get(
            f"{BASE_URL}/summary?month={int(month)}&year={int(year)}"
        )

        data = res.json()

        if "error" in data:
            return f"❌ {data['error']}"

        income = float(data.get("total_income", 0))
        expense = float(data.get("total_expense", 0))

        if income == 0 and expense == 0:
            return "⚠️ No data available for this month"

        fig, ax = plt.subplots()

        ax.pie(
            [income, expense],
            labels=["Income", "Expense"],
            autopct='%1.1f%%'
        )

        ax.set_title(f"Month {int(month)} Summary")

        return fig

    except Exception as e:
        logging.error(f"Monthly graph error: {e}")
        return None


# 📈 YEARLY GRAPH
def yearly_graph_fn(year):
    logging.info(f"Yearly graph for {year}")

    try:
        res = requests.get(f"{BASE_URL}/test")
        data = res.json()

        df = pd.DataFrame(data)

        if df.empty:
            return "⚠️ No data available"

        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        df["Month"] = df["Date"].dt.month
        df["Year"] = df["Date"].dt.year

        df = df[df["Year"] == int(year)]

        income = df[df["Type"] == "income"].groupby("Month")["Amount"].sum()
        expense = df[df["Type"] == "expense"].groupby("Month")["Amount"].sum()

        months = list(range(1, 13))

        income_vals = [income.get(m, 0) for m in months]
        expense_vals = [expense.get(m, 0) for m in months]

        fig, ax = plt.subplots()

        ax.plot(months, income_vals, marker='o', label="Income")
        ax.plot(months, expense_vals, marker='o', label="Expense")

        ax.legend()
        ax.set_title(f"Year {int(year)} Summary")
        ax.set_xlabel("Month")
        ax.set_ylabel("Amount")

        return fig

    except Exception as e:
        logging.error(f"Yearly graph error: {e}")
        return None


# 🎨 UI
with gr.Blocks() as demo:

    gr.Markdown("## 💰 Finance Chatbot")

    # 💬 CHAT UI
    chat_input = gr.Textbox(label="Enter message")
    chat_output = gr.Textbox(label="Response")

    # ✅ UPDATED LINE (clears input)
    chat_input.submit(chat_fn, inputs=chat_input, outputs=[chat_output, chat_input])

    # 📋 ADMIN PANEL
    gr.Markdown("## 📋 Admin Panel")
    table = gr.Dataframe()
    btn = gr.Button("Load Data")

    btn.click(admin_fn, outputs=table)

    # 📊 MONTHLY GRAPH
    gr.Markdown("## 📊 Monthly Graph")

    month_input = gr.Number(label="Month (1-12)")
    year_input1 = gr.Number(label="Year")

    monthly_graph = gr.Plot()
    monthly_btn = gr.Button("Show Monthly Graph")

    monthly_btn.click(
        monthly_graph_fn,
        inputs=[month_input, year_input1],
        outputs=monthly_graph
    )

    # 📈 YEARLY GRAPH
    gr.Markdown("## 📈 Yearly Graph")

    year_input2 = gr.Number(label="Year")

    yearly_graph = gr.Plot()
    yearly_btn = gr.Button("Show Yearly Graph")

    yearly_btn.click(
        yearly_graph_fn,
        inputs=year_input2,
        outputs=yearly_graph
    )


# 🚀 Launch
demo.launch()