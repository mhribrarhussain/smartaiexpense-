import sqlite3
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

DB_NAME = "expenses.db"

def get_connection():
    """Establishes and returns a database connection."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row  # Access columns by name
    return conn

def init_db():
    """Initializes the database with users and expenses tables."""
    conn = get_connection()
    c = conn.cursor()
    
    # Create Users Table - Added security_pin
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            security_pin TEXT
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            expense_text TEXT NOT NULL,
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            date TEXT NOT NULL,
            user_id INTEGER,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    ''')
    
    conn.commit()
    conn.close()

def register_user(username, password, security_pin):
    """Registers a new user with a security PIN."""
    conn = get_connection()
    c = conn.cursor()
    password_hash = generate_password_hash(password)
    
    try:
        # Store security_pin as text suitable for exact matching (could hash it too for extra security, but keeping simple for this scope)
        c.execute("INSERT INTO users (username, password_hash, security_pin) VALUES (?, ?, ?)", 
                  (username, password_hash, security_pin))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def check_user(username, password):
    """Verifies user credentials."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT user_id, password_hash FROM users WHERE username = ?", (username,))
    user = c.fetchone()
    conn.close()
    
    if user and check_password_hash(user['password_hash'], password):
        return user['user_id']
    return None

def check_security_pin(username, pin):
    """Verifies if the PIN matches the username."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT security_pin FROM users WHERE username = ?", (username,))
    user = c.fetchone()
    conn.close()
    
    if user and user['security_pin'] == pin:
        return True
    return False

def update_password(username, new_password):
    """Updates password for a user."""
    conn = get_connection()
    c = conn.cursor()
    password_hash = generate_password_hash(new_password)
    c.execute("UPDATE users SET password_hash = ? WHERE username = ?", (password_hash, username))
    conn.commit()
    conn.close()

def add_expense(expense_text, amount, category, user_id, custom_date=None):
    """Adds a new expense linked to a user. Supports backdating."""
    conn = get_connection()
    c = conn.cursor()
    
    # Use custom date if provided, else use current time
    if custom_date:
        # Assuming input is YYYY-MM-DD, append current time for consistency or default time
        date_str = f"{custom_date} {datetime.now().strftime('%H:%M:%S')}"
    else:
        date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
    c.execute('''
        INSERT INTO expenses (expense_text, amount, category, date, user_id)
        VALUES (?, ?, ?, ?, ?)
    ''', (expense_text, amount, category, date_str, user_id))
    conn.commit()
    conn.close()

def get_expenses(user_id=None, month=None):
    """Retrieves expenses filtered by user_id and optionally by month."""
    conn = get_connection()
    c = conn.cursor()
    
    query = "SELECT * FROM expenses WHERE 1=1"
    params = []
    
    if user_id:
        query += " AND user_id = ?"
        params.append(user_id)
        
    if month:
        query += " AND strftime('%Y-%m', date) = ?"
        params.append(month)
        
    c.execute(query, params)
    rows = c.fetchall()
    conn.close()
    return rows

def get_all_expenses_as_dataframe(user_id=None):
    import pandas as pd
    conn = get_connection()
    query = "SELECT * FROM expenses"
    params = []
    if user_id:
        query += " WHERE user_id = ?"
        params.append(user_id)
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df

def delete_expense(expense_id, user_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM expenses WHERE id = ? AND user_id = ?", (expense_id, user_id))
    conn.commit()
    conn.close()

def update_expense(expense_id, user_id, text, amount, category):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        UPDATE expenses 
        SET expense_text = ?, amount = ?, category = ?
        WHERE id = ? AND user_id = ?
    """, (text, amount, category, expense_id, user_id))
    conn.commit()
    conn.close()

def get_expense_by_id(expense_id, user_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM expenses WHERE id = ? AND user_id = ?", (expense_id, user_id))
    row = c.fetchone()
    conn.close()
    return row
