import gradio as gr
import pandas as pd
import matplotlib.pyplot as plt

# Import functions from backend
from app import add_expense_logic, get_all_data, get_monthly_summary,get_yearly_summary


# 💬 Chat function
def chat_fn(message):
    return add_expense_logic(message)


# 📋 Admin table
def admin_fn():
    data = get_all_data()
    return pd.DataFrame(data)


# 📊 Graph function
def monthly_graph_fn(month, year):
    summary = get_monthly_summary(month, year)

    income = summary["income"]
    expense = summary["expense"]

    labels = ["Income", "Expense"]
    values = [income, expense]

    plt.figure()

    plt.pie(values, labels=labels, autopct='%1.1f%%')
    plt.title(f"Month {month} Distribution")

    return plt

def yearly_graph_fn(year):
    income, expense = get_yearly_summary(year)

    months = list(range(1, 13))

    income_vals = [income.get(m, 0) for m in months]
    expense_vals = [expense.get(m, 0) for m in months]

    plt.figure()
    plt.plot(months, income_vals, marker='o', label="Income")
    plt.plot(months, expense_vals, marker='o', label="Expense")

    plt.legend()
    plt.title(f"Year {year} Summary")
    plt.grid()

    return plt

# 🎨 UI
with gr.Blocks() as demo:

    gr.Markdown("## 💰 Finance Chatbot")

    # 💬 Chat
    chat_input = gr.Textbox(label="Enter message")
    chat_output = gr.Textbox(label="Response")

    chat_input.submit(chat_fn, chat_input, chat_output)

    # 📋 Admin Panel
    gr.Markdown("## 📋 Admin Panel")
    table = gr.Dataframe()
    btn = gr.Button("Load Data")

    btn.click(admin_fn, outputs=table)

    # 📊 Monthly Graph
    gr.Markdown("## 📊 Monthly Graph")

    month_input = gr.Number(label="Enter Month (1-12)")
    year_input1 = gr.Number(label="Enter Year")

    monthly_graph = gr.Plot()
    monthly_btn = gr.Button("Show Monthly Graph")

    monthly_btn.click(
        monthly_graph_fn,
        inputs=[month_input, year_input1],
        outputs=monthly_graph
    )

    # 📈 Yearly Graph
    gr.Markdown("## 📈 Yearly Graph")

    year_input2 = gr.Number(label="Enter Year")

    yearly_graph = gr.Plot()
    yearly_btn = gr.Button("Show Yearly Graph")

    yearly_btn.click(
        yearly_graph_fn,
        inputs=year_input2,
        outputs=yearly_graph
    )


# 🚀 Launch
demo.launch()
