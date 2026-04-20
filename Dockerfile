FROM python:3.11

WORKDIR /app

COPY . /app

RUN pip install --no-cache-dir --default-timeout=100 -r requirements.txt

EXPOSE 7860

CMD ["python", "gradio_app.py"]