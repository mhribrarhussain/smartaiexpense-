import database
import pandas as pd
from datetime import datetime

def get_monthly_total(user_id):
    """Calculates total spending for the current month for a specific user."""
    current_month = datetime.now().strftime("%Y-%m")
    expenses = database.get_expenses(user_id=user_id, month=current_month)
    total = sum(row['amount'] for row in expenses)
    return total

def get_category_breakdown(user_id):
    """Calculates spending per category for the current month for a specific user."""
    current_month = datetime.now().strftime("%Y-%m")
    expenses = database.get_expenses(user_id=user_id, month=current_month)
    
    breakdown = {}
    for row in expenses:
        cat = row['category']
        amt = row['amount']
        breakdown[cat] = breakdown.get(cat, 0) + amt
    
    return breakdown

def generate_suggestions(user_id):
    """Generates simple financial suggestions based on thresholds for a user."""
    breakdown = get_category_breakdown(user_id)
    suggestions = []
    
    # Thresholds for 10 Categories (in PKR)
    thresholds = {
        "Food & Dining": 30000,
        "Transportation": 15000,
        "Housing & Utilities": 50000,
        "Mobile & Communication": 3000,
        "Shopping": 20000,
        "Health & Fitness": 10000,
        "Education": 25000,
        "Entertainment": 5000,
        "Gifts & Donations": 10000,
        "Financial / Others": 20000
    }
    
    for category, amount in breakdown.items():
        limit = thresholds.get(category, 20000)
        if amount > limit:
            suggestions.append(f"⚠️  Alert: High spending in {category} (PKR {amount} > Limit {limit}).")
    
    total_spending = get_monthly_total(user_id)
    if total_spending > 100000:
        suggestions.append("⚠️  Alert: Total monthly spending is high (> PKR 100,000).")
    
    if not suggestions:
        suggestions.append("✅ Great job! Your spending is within limits.")
        
    return suggestions

def predict_next_month_spending(user_id):
    """Predicts next month's spending using Linear Regression on daily totals."""
    try:
        from sklearn.linear_model import LinearRegression
        import numpy as np
        import pandas as pd
        
        # Get daily spending
        daily = get_daily_spending(user_id)
        
        # Scenario 1: No Data
        if not daily:
            return 0
            
        # Scenario 2: Only 1 Day of Data (Simple Extrapolation)
        if len(daily) == 1:
            val = list(daily.values())[0]
            return val * 30 # Simple projection
            
        # Scenario 3: 2+ Days (Linear Regression)
            
        # Prepare data: X = Day number, y = Cumulative Amount
        # (Using cumulative gives a smoother trend for monthly projection)
        df = pd.DataFrame(list(daily.items()), columns=['date', 'amount'])
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')
        df['day'] = (df['date'] - df['date'].min()).dt.days
        df['cumulative'] = df['amount'].cumsum()
        
        X = df[['day']]
        y = df['cumulative']
        
        model = LinearRegression()
        model.fit(X, y)
        
        # Predict for day 30
        next_val = model.predict([[30]])[0]
        return max(0, round(next_val, 2))
    except Exception as e:
        print(f"Prediction Error: {e}")
        return 0

def detect_anomalies(user_id):
    """Detects unusual expenses using Isolation Forest."""
    try:
        from sklearn.ensemble import IsolationForest
        import pandas as pd
        
        expenses = database.get_expenses(user_id=user_id)
        if len(expenses) < 5:
            return []
            
        df = pd.DataFrame([{'amount': e['amount'], 'id': e['id'], 'text': e['expense_text']} for e in expenses])
        
        # Train on 'amount'
        model = IsolationForest(contamination=0.05, random_state=42)
        df['anomaly'] = model.fit_predict(df[['amount']])
        
        # -1 indicates anomaly
        anomalies = df[df['anomaly'] == -1]
        results = []
        for _, row in anomalies.iterrows():
            results.append(f"⚠️ Anomaly: {row['text']} (PKR {row['amount']}) seems unusual.")
            
        return results
    except Exception as e:
        print(f"Anomaly Error: {e}")
        return []

def get_daily_spending(user_id):
    """Calculates total spending per day for the current month for a user."""
    current_month = datetime.now().strftime("%Y-%m")
    expenses = database.get_expenses(user_id=user_id, month=current_month)
    
    daily = {}
    for row in expenses:
        day = row['date'].split(" ")[0]
        amt = row['amount']
        daily[day] = daily.get(day, 0) + amt
    
    return dict(sorted(daily.items()))
