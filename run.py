from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, make_response
import database
from ai_engine import classifier as ai_classifier
from ai_engine import analytics as ai_analytics
from ai_engine import ocr as ai_ocr
from ai_engine import chatbot as ai_chatbot
import re
import os
from functools import wraps
from werkzeug.utils import secure_filename
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'super_secret_key_for_university_project'
UPLOAD_FOLDER = os.path.join('static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Initialize System
database.init_db()
classifier = ai_classifier.ExpenseClassifier()
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
    """
    Parses natural language input into multiple transactions.
    Example: "pizza 700 cooking oil 700 cigs 150"
    Returns: List of (text, amount) tuples.
    """
    # Helper to clean text
    def clean(t): return t.strip().strip(',').strip('and').strip()

    # Regex pattern: (Words/Spaces) followed by (Number)
    # This logic splits the string by numbers to find multiple items
    items = []
    
    # Strategy: Find all numbers first, then split text around them
    # Better Regex: Look for groups of (Text)(Number)
    pattern = re.compile(r'([a-zA-Z\s,]+?)(\d+(?:\.\d+)?)')
    matches = pattern.findall(user_input)
    
    for text, amount_str in matches:
        desc = clean(text)
        if desc:
            try:
                amt = float(amount_str)
                items.append((desc, amt))
            except:
                continue
                
    # Fallback for simple "Biryani 300" if complex regex misses
    if not items:
        # Old logic as fallback
        match = re.search(r'(\d+(\.\d+)?)', user_input)
        if match:
            amount = float(match.group(1))
            text = user_input.replace(match.group(1), "").strip()
            items.append((text, amount))
            
    return items

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
    return render_template('login.html', page_title="Login")

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        pin = request.form['pin']
        if database.register_user(username, password, pin):
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Username already exists.', 'error')
    return render_template('register.html', page_title="Register")

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        username = request.form['username']
        pin = request.form['pin']
        new_password = request.form['new_password']
        
        if database.check_security_pin(username, pin):
            database.update_password(username, new_password)
            flash('Password reset successfully! Please login.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Invalid Username or PIN.', 'error')
            
    return render_template('forgot_password.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    user_id = session['user_id']
    username = session['username']
    
    # Fetch Data
    expenses = database.get_expenses(user_id=user_id)
    # Sort by Date descending (Newest date first), then by ID (for same date)
    expenses.sort(key=lambda x: (x['date'], x['id']), reverse=True)
    total = ai_analytics.get_monthly_total(user_id)
    suggestions = ai_analytics.generate_suggestions(user_id)
    
    # Advanced AI
    forecast = ai_analytics.predict_next_month_spending(user_id)
    anomalies = ai_analytics.detect_anomalies(user_id)
    
    current_date = datetime.now().strftime("%B %d, %Y")
    
    return render_template('dashboard.html', 
                           page_title="Dashboard",
                           active_page="dashboard",
                           username=username, 
                           expenses=expenses[:5],
                           total=total, 
                           suggestions=suggestions,
                           anomalies=anomalies,
                           forecast=forecast,
                           current_date=current_date)

@app.route('/chat')
@login_required
def chat_page():
    username = session['username']
    return render_template('chat.html', 
                           page_title="Result", 
                           active_page="chat",
                           username=username)

@app.route('/api/chat', methods=['POST'])
@login_required
def chat_api():
    data = request.get_json()
    message = data.get('message', '')
    user_id = session['user_id']
    username = session['username']
    response = ai_chatbot.process_query(message, user_id, username)
    return jsonify({'response': response})

@app.route('/history')
@login_required
def history():
    user_id = session['user_id']
    username = session['username']
    
    expenses = database.get_expenses(user_id=user_id)
    # Sort by Date descending so backdated entries appear correctly in timeline
    expenses.sort(key=lambda x: (x['date'], x['id']), reverse=True)
    
    # Group by category
    categorized_expenses = {}
    for expense in expenses:
        cat = expense['category']
        if cat not in categorized_expenses:
            categorized_expenses[cat] = {'entries': [], 'total': 0}
        categorized_expenses[cat]['entries'].append(expense)
        categorized_expenses[cat]['total'] += expense['amount']
    
    return render_template('history.html', 
                           page_title="History",
                           active_page="history",
                           username=username,
                           categorized_expenses=categorized_expenses)

@app.route('/settings')
@login_required
def settings():
    username = session['username']
    return render_template('settings.html',
                           page_title="Settings",
                           active_page="settings",
                           username=username)

@app.route('/change_password', methods=['POST'])
@login_required
def change_password():
    new_password = request.form['new_password']
    username = session['username']
    database.update_password(username, new_password)
    flash('Password updated successfully.', 'success')
    return redirect(url_for('settings'))

@app.route('/export_pdf')
@login_required
def export_pdf():
    from fpdf import FPDF
    
    user_id = session['user_id']
    username = session['username']
    expenses = database.get_expenses(user_id=user_id)
    total = ai_analytics.get_monthly_total(user_id)
    forecast = ai_analytics.predict_next_month_spending(user_id)
    current_date = datetime.now().strftime("%B %d, %Y")
    
    class PDF(FPDF):
        def header(self):
            self.set_font('Arial', 'B', 15)
            self.cell(0, 10, 'Smart AI Expense Manager - User Report', 0, 1, 'C')
            self.ln(5)

        def footer(self):
            self.set_y(-15)
            self.set_font('Arial', 'I', 8)
            self.cell(0, 10, 'Page ' + str(self.page_no()) + ' | Generated by AI System', 0, 0, 'C')

    pdf = PDF()
    pdf.add_page()
    
    # 1. User Info Section
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=f"User: {username}", ln=True)
    pdf.cell(200, 10, txt=f"Date: {current_date}", ln=True)
    pdf.ln(5)
    
    # 2. Financial Summary Box
    pdf.set_fill_color(240, 240, 240)
    pdf.rect(10, 45, 190, 30, 'F')
    pdf.set_yy = 50 
    
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(95, 10, f"Total Spending (This Month):", 0, 0)
    pdf.set_font("Arial", '', 12)
    pdf.cell(95, 10, f"PKR {total}", 0, 1)
    
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(95, 10, f"Forecast (Next Month):", 0, 0)
    pdf.set_font("Arial", '', 12)
    pdf.cell(95, 10, f"PKR {forecast}", 0, 1)
    
    pdf.ln(15)
    
    # 3. Transactions Table
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(200, 10, txt="Detailed Transaction History", ln=True)
    pdf.ln(2)
    
    # Table Header
    pdf.set_font("Arial", 'B', 10)
    pdf.set_fill_color(200, 200, 200)
    pdf.cell(30, 10, 'Date', 1, 0, 'C', 1)
    pdf.cell(50, 10, 'Category', 1, 0, 'C', 1)
    pdf.cell(80, 10, 'Description', 1, 0, 'C', 1)
    pdf.cell(30, 10, 'Amount', 1, 1, 'C', 1)
    
    # Table Rows
    pdf.set_font("Arial", '', 10)
    for e in expenses:
        # Date: Remove time if present (take first 10 chars "YYYY-MM-DD")
        date_str = str(e['date']).split(' ')[0]
        pdf.cell(30, 10, date_str, 1)
        pdf.cell(50, 10, str(e['category']), 1)
        pdf.cell(80, 10, str(e['expense_text'])[:40], 1) # Truncate long text
        pdf.cell(30, 10, f"PKR {e['amount']}", 1, 1)
        
    response = make_response(pdf.output(dest='S').encode('latin-1'))
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'attachment; filename=SmartExpense_Report.pdf'
    return response

@app.route('/delete_expense/<int:expense_id>', methods=['POST'])
@login_required
def delete_expense_route(expense_id):
    database.delete_expense(expense_id, session['user_id'])
    flash('Transaction deleted successfully.', 'success')
    return redirect(url_for('history'))

@app.route('/edit_expense/<int:expense_id>', methods=['GET'])
@login_required
def edit_expense_page(expense_id):
    expense = database.get_expense_by_id(expense_id, session['user_id'])
    if not expense:
        flash('Transaction not found.', 'error')
        return redirect(url_for('history'))
    return render_template('edit_expense.html', page_title="Edit Expense", active_page="history", expense=expense, username=session['username'])

@app.route('/update_expense/<int:expense_id>', methods=['POST'])
@login_required
def update_expense_route(expense_id):
    text = request.form['text']
    amount = float(request.form['amount'])
    category = request.form['category']
    database.update_expense(expense_id, session['user_id'], text, amount, category)
    flash('Transaction updated successfully.', 'success')
    return redirect(url_for('history'))

@app.route('/reset_account', methods=['POST'])
@login_required
def reset_account():
    # In a real app, require password confirmation here
    user_id = session['user_id']
    conn = database.get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM expenses WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()
    flash('All your data has been reset.', 'warning')
    return redirect(url_for('settings'))

@app.route('/update_settings', methods=['POST'])
@login_required
def update_settings():
    # Placeholder for saving currency/profile preferences
    flash('Settings saved successfully.', 'success')
    return redirect(url_for('settings'))

@app.route('/add_expense', methods=['POST'])
@login_required
def add_expense_route():
    raw_input = request.form['raw_input']
    custom_date = request.form.get('expense_date') # Optional date from form
    
    items = parse_input(raw_input)
    
    if items:
        count = 0
        for text, amount in items:
            category = classifier.predict(text)
            database.add_expense(text, amount, category, session['user_id'], custom_date)
            count += 1
        
        if count == 1:
            # Single item message
            flash(f'Added: {items[0][0]} (PKR {items[0][1]}) - {category}', 'success')
        else:
            # Multi item message
            flash(f'Successfully added {count} separate expenses!', 'success')
    else:
        flash('Could not understand input. Try format "Item 100 Item 200"', 'error')
    return redirect(url_for('dashboard'))

@app.route('/upload_receipt', methods=['POST'])
@login_required
def upload_receipt():
    if 'receipt' not in request.files:
        flash('No file part', 'error')
        return redirect(url_for('dashboard'))
        
    file = request.files['receipt']
    if file.filename == '' or not file:
        flash('No selected file', 'error')
        return redirect(url_for('dashboard'))
        
    filename = secure_filename(file.filename)
    path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(path)
    
    text = ai_ocr.extract_text(path)
    
    # Feature #4: Try to find multiple items first
    items = ai_ocr.parse_receipt_items(text)
    
    if items:
        count = 0
        total_added = 0
        for item in items:
            cat = classifier.predict(item['desc'])
            database.add_expense(item['desc'], item['amount'], cat, session['user_id'])
            count += 1
            total_added += item['amount']
        flash(f'Receipt Processed! Added {count} items totaling PKR {total_added}. Check History.', 'success')
    else:
        # Fallback to simple Total parsing if no items found
        desc, amount = ai_ocr.parse_receipt(text)
        category = classifier.predict(desc if desc else "Receipt")
        
        if amount > 0:
            database.add_expense(desc, amount, category, session['user_id'])
            flash(f'Receipt Scanned! Added: {desc} (PKR {amount}) - {category}', 'success')
        else:
            flash('Could not read receipt clearly. Please add manually.', 'warning')
             
    return redirect(url_for('dashboard'))

@app.route('/api/chart_data')
@login_required
def chart_data():
    user_id = session['user_id']
    breakdown = ai_analytics.get_category_breakdown(user_id)
    daily = ai_analytics.get_daily_spending(user_id)
    
    return jsonify({
        "categories": list(breakdown.keys()),
        "category_amounts": list(breakdown.values()),
        "dates": list(daily.keys()),
        "daily_amounts": list(daily.values())
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)
