# Smart Expense Manager

A Python-based AI agent to track expenses, classify them automatically using Machine Learning, and provide spending analysis.

## Features
- **AI Categorization**: Uses a Naive Bayes classifier (TF-IDF) to automatically categorize expenses like "Pizza 1200" into "Food".
- **SQLite Storage**: Saves all data locally in `expenses.db`.
- **Spending Analysis**: View monthly totals, category breakdowns, and receive spending alerts.

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run the application:
   ```bash
   python main.py
   ```

## Usage
- **Add Expense**: Type text like `Uber 500`. The AI will predict if it's Travel, Food, etc. You can confirm or correct it.
- **View Analysis**: See your detailed spending breakdown.
