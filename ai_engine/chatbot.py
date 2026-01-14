import re
import database
from . import analytics

def process_query(text, user_id, username="User"):
    text = text.lower()
    
    # Intent: Greetings & Politeness
    if any(x in text for x in ["hi", "hello", "hey", "salam"]):
        return f"Hello {username}! 👋 How can I help you manage your budget today?"
        
    if any(x in text for x in ["thank", "thanks", "good job"]):
        return "You're welcome! Happy to help. 😊"

    # Intent: Total Spending
    if any(x in text for x in ["total", "spent", "spending", "how much", "cost"]):
        if any(c in text for c in ["food", "transport", "travel", "utility", "bills", "shopping", "health", "education", "gift", "donation"]):
            return _handle_category_query(text, user_id)
        return _handle_total_query(user_id)
        
    # Intent: Prediction
    if "predict" in text or "next month" in text or "forecast" in text:
        prediction = analytics.predict_next_month_spending(user_id)
        return f"Based on your current trend, I predict you will spend around **PKR {prediction}** next month. 🔮"
        
    # Intent: Anomalies
    if "weird" in text or "anomaly" in text or "strange" in text:
        anomalies = analytics.detect_anomalies(user_id)
        if anomalies:
            return "⚠️ I found these unusual transactions:<br>" + "<br>".join(anomalies)
        return "✅ Everything looks normal! No anomalies detected."
        
    # Intent: Smart Analysis (LLM Simulation)
    if any(x in text for x in ["analyze", "advice", "audit", "save", "review", "report", "suggestion"]):
        return _generate_smart_analysis(user_id, username)

    # Default
    return "I am an AI Budget Assistant. 🤖<br>Ask me things like:<br>👉 'How much did I spend on Food?'<br>👉 'Predict my spending'<br>👉 'Analyze my budget'"

def _handle_total_query(user_id):
    total = analytics.get_monthly_total(user_id)
    return f"You have spent a total of **PKR {total}** this month."

def _handle_category_query(text, user_id):
    breakdown = analytics.get_category_breakdown(user_id)
    # Simple keyword matching
    found_cat = None
    
    categories = {
        "food": "Food & Dining",
        "mess": "Transportation", # User specific override maybe?
        "transport": "Transportation",
        "careem": "Transportation",
        "fuel": "Transportation",
        "bill": "Housing & Utilities",
        "util": "Housing & Utilities",
        "shop": "Shopping",
        "health": "Health & Fitness",
        "edu": "Education",
        "book": "Education"
    }
    
    target = next((cat for key, cat in categories.items() if key in text), "Unknown")
    
    if target != "Unknown":
        amount = breakdown.get(target, 0)
        return f"You have spent **PKR {amount}** on {target}."
    
    return "I couldn't identify the category. Try checking your dashboard."

def _generate_smart_analysis(user_id, username):
    """
    Simulates a Generative AI analysis by constructing a data-driven narrative.
    """
    total = analytics.get_monthly_total(user_id)
    breakdown = analytics.get_category_breakdown(user_id)
    anomalies = analytics.detect_anomalies(user_id)
    forecast = analytics.predict_next_month_spending(user_id)
    
    # 1. Find Highest Category
    if not breakdown:
        return "I need more data to analyze your spending habits! Start adding expenses."
        
    highest_cat = max(breakdown, key=breakdown.get)
    highest_amt = breakdown[highest_cat]
    percentage = int((highest_amt / total) * 100) if total > 0 else 0
    
    # 2. Construct Narrative
    response = f"📊 **Financial Health Report for {username}**<br><br>"
    
    # Overview
    response += f"You have spent **PKR {total}** so far. Based on your current pace, I forecast you'll hit **PKR {forecast}** by next month.<br><br>"
    
    # Insight
    response += f"⚠️ **Key Insight:** Your biggest expense is **{highest_cat}** ({percentage}% of total). "
    
    if "Food" in highest_cat and percentage > 40:
        response += "You are spending a lot on eating out. Try cooking at home to save ~15%. 🍳<br>"
    elif "Transport" in highest_cat and percentage > 30:
        response += "Transport costs are high. Consider carpooling or using public transport? 🚌<br>"
    else:
        response += "Consider setting a strict budget for this category.<br>"
        
    # Anomalies
    if anomalies:
        response += f"<br>👀 **Watch Out:** I found {len(anomalies)} unusual transactions. Check the dashboard."
        
    response += "<br><br>💡 **Recommendation:** Try the '50-30-20 Rule'. Allocate 50% to Needs, 30% to Wants, and 20% to Savings."
    
    return response
