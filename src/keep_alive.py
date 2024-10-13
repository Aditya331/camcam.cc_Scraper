from flask import Flask, render_template
from threading import Thread
import logging

app = Flask('')

# Shared variables for progress tracking and logs
progress = 0
max_progress = 100
log_messages = []

@app.route('/')
def home():
    return render_template('index.html', progress=progress, log_messages=log_messages)

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

def update_progress(value):
    global progress
    progress = value

def add_log_message(message):
    global log_messages
    log_messages.append(message)
    if len(log_messages) > 100:  # Limit log size to 100 messages
        log_messages = log_messages[-100:]
