import gradio as gr
import pandas as pd
import matplotlib.pyplot as plt
import logging

# 🔐 Logging setup
logging.basicConfig(
    filename="app.log",   # saves logs to file
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

logging.info("🚀 Gradio App Started")

# Import functions from backend
from app import add_expense_logic, get_all_data, get_monthly_summary, get_yearly_summary


# 💬 Chat function
def chat_fn(message):
    logging.info(f"Chat input received: {message}")
    try:
        response = add_expense_logic(message)
        logging.info(f"Chat response sent: {response}")
        return response
    except Exception as e:
        logging.error(f"Error in chat_fn: {e}")
        return "Error processing your request"


# 📋 Admin table
def admin_fn():
    logging.info("Admin panel requested data")
    try:
        data = get_all_data()
        logging.info(f"Fetched {len(data)} records from database")
        return pd.DataFrame(data)
    except Exception as e:
        logging.error(f"Error fetching admin data: {e}")
        return pd.DataFrame()


# 📊 Monthly Graph function
def monthly_graph_fn(month, year):
    logging.info(f"Generating monthly graph for Month={month}, Year={year}")
    try:
        summary = get_monthly_summary(month, year)

        income = summary["income"]
        expense = summary["expense"]

        labels = ["Income", "Expense"]
        values = [income, expense]

        plt.figure()
        plt.pie(values, labels=labels, autopct='%1.1f%%')
        plt.title(f"Month {month} Distribution")

        logging.info("Monthly graph generated successfully")
        return plt
    except Exception as e:
        logging.error(f"Error generating monthly graph: {e}")
        return plt


# 📈 Yearly Graph function
def yearly_graph_fn(year):
    logging.info(f"Generating yearly graph for Year={year}")
    try:
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

        logging.info("Yearly graph generated successfully")
        return plt
    except Exception as e:
        logging.error(f"Error generating yearly graph: {e}")
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



