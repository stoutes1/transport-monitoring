from flask import render_template
from . import create_app

app = create_app()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/data')
def get_data():
    return {"status": "OK", "version": "1.0.0"}