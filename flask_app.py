from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import database
import model
import analysis
import ocr
import re
import os
from functools import wraps
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'super_secret_key_for_university_project'
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

database.init_db()
classifier = model.ExpenseClassifier()
try:
    classifier.load_model()
except:
    classifier.train()

# --- Helpers ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def parse_input(user_input):
    match = re.search(r'(\d+(\.\d+)?)', user_input)
    if not match:
        return None, None
    amount = float(match.group(1))
    text = user_input.replace(match.group(1), "").strip()
    return text, amount

# --- Routes ---
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user_id = database.check_user(username, password)
        if user_id:
            session['user_id'] = user_id
            session['username'] = username
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'error')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if database.register_user(username, password):
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Username already exists.', 'error')
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    user_id = session['user_id']
    username = session['username']
    expenses = database.get_expenses(user_id=user_id)
    expenses.sort(key=lambda x: x['id'], reverse=True)
    total = analysis.get_monthly_total(user_id)
    suggestions = analysis.generate_suggestions(user_id)
    
    return render_template('dashboard.html', 
                           username=username, 
                           expenses=expenses, 
                           total=total, 
                           suggestions=suggestions)

@app.route('/add_expense', methods=['POST'])
@login_required
def add_expense_route():
    raw_input = request.form['raw_input']
    text, amount = parse_input(raw_input)
    if text and amount:
        category = classifier.predict(text)
        database.add_expense(text, amount, category, session['user_id'])
        flash(f'Added: {text} (PKR {amount}) - Category: {category}', 'success')
    else:
        flash('Could not understand input.', 'error')
    return redirect(url_for('dashboard'))

@app.route('/upload_receipt', methods=['POST'])
@login_required
def upload_receipt():
    if 'receipt' not in request.files:
        flash('No file part', 'error')
        return redirect(url_for('dashboard'))
        
    file = request.files['receipt']
    if file.filename == '':
        flash('No selected file', 'error')
        return redirect(url_for('dashboard'))
        
    if file:
        filename = secure_filename(file.filename)
        path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(path)
        
        # OCR Processing
        text = ocr.extract_text(path)
        desc, amount = ocr.parse_receipt(text)
        
        # Determine category (use full text for better context)
        category = classifier.predict(text if text else "Receipt")
        
        if amount > 0:
            database.add_expense(desc, amount, category, session['user_id'])
            flash(f'Receipt Scanned! Added: {desc} (PKR {amount}) - {category}', 'success')
        else:
             flash('Could not defect amount from receipt. Please add manually.', 'error')
             
    return redirect(url_for('dashboard'))

@app.route('/api/chart_data')
@login_required
def chart_data():
    user_id = session['user_id']
    breakdown = analysis.get_category_breakdown(user_id)
    daily = analysis.get_daily_spending(user_id)
    
    return jsonify({
        "categories": list(breakdown.keys()),
        "category_amounts": list(breakdown.values()),
        "dates": list(daily.keys()),
        "daily_amounts": list(daily.values())
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)
