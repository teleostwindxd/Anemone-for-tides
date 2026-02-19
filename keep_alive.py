from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "Bot is alive and running!"

def run():
    # Render expects web services to bind to 0.0.0.0 on a specific port (defaults to 10000)
    app.run(host='0.0.0.0', port=10000)

def keep_alive():
    t = Thread(target=run)
    t.start()
