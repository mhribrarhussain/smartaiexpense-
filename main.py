import re
import sys
import database
import model
import analysis
from datetime import datetime

class SmartExpenseManager:
    def __init__(self):
        print("Initializing Smart Expense Manager...")
        database.init_db()
        self.classifier = model.ExpenseClassifier()
        # Ensure model is trained on startup
        try:
            self.classifier.load_model()
        except:
             # Basic handling if load fails (though load_model handles it)
            self.classifier.train()

    def parse_input(self, user_input):
        """Extracts text and amount from input string.
           Expected formats: "Pizza 1200", "1200 Pizza", "Uber 500", etc.
        """
        # Regex to find the last or first number in the string
        # Match integer or float amounts (e.g. 1200, 1200.50)
        match = re.search(r'(\d+(\.\d+)?)', user_input)
        
        if not match:
            return None, None
            
        amount_str = match.group(1)
        amount = float(amount_str)
        
        # Remove the amount from the text to get the description
        text = user_input.replace(amount_str, "").strip()
        
        # Cleanup extra non-alphanumeric chars if any, but keep simple for now
        return text, amount

    def add_expense_flow(self):
        print("\n--- Add New Expense ---")
        print("Enter expense description and amount (e.g., 'Pizza 1200', 'Uber 500'). Type 'back' to cancel.")
        user_input = input(">> ")
        
        if user_input.lower() == 'back':
            return

        text, amount = self.parse_input(user_input)
        
        if not text or amount is None:
            print("❌ Error: Could not understand input. Please include both text and amount.")
            return

        print(f"Analyzing expense: '{text}' ($ {amount}) ...")
        category = self.classifier.predict(text)
        
        print(f"🤖 AI Categorized as: [ {category} ]")
        confirm = input(f"Is this correct? (y/n): ").strip().lower()
        
        final_category = category
        if confirm != 'y':
            print("Select correct category:")
            cats = ["Food", "Travel", "Bills", "Shopping", "Health", "Others"]
            for i, c in enumerate(cats):
                print(f"{i+1}. {c}")
            try:
                choice = int(input("Enter choice (1-6): "))
                final_category = cats[choice-1]
            except:
                print("Invalid choice, keeping AI prediction.")
        
        database.add_expense(text, amount, final_category)
        print("✅ Expense saved successfully!")

    def view_analysis_flow(self):
        print("\n--- Financial Analysis ---")
        total = analysis.get_monthly_total()
        breakdown = analysis.get_category_breakdown()
        suggestions = analysis.generate_suggestions()
        
        print(f"📅 Current Month Total: {total}")
        print("\n📊 Category Breakdown:")
        if not breakdown:
            print("   No expenses recorded this month.")
        else:
            for cat, amt in breakdown.items():
                print(f"   - {cat}: {amt}")
        
        print("\n💡 AI Suggestions:")
        for sugg in suggestions:
            print(f"   {sugg}")

    def run(self):
        print("\n==========================================")
        print(" 💰 SMART EXPENSE MANAGER AI 💰")
        print("==========================================")
        
        while True:
            print("\nMAIN MENU:")
            print("1. Add Expense")
            print("2. View Analysis")
            print("3. Show All Expenses")
            print("4. Exit")
            
            try:
                choice = input("Select option: ").strip()
            except KeyboardInterrupt:
                print("\nExiting...")
                break
                
            if choice == '1':
                self.add_expense_flow()
            elif choice == '2':
                self.view_analysis_flow()
            elif choice == '3':
                # Quick dump of recent expenses
                params = input("Press Enter for full list or type 'month' for this month only: ")
                month = datetime.now().strftime("%Y-%m") if 'month' in params else None
                rows = database.get_expenses(month)
                print(f"\n--- {'This Month' if month else 'All'} Expenses ({len(rows)}) ---")
                for row in rows:
                    print(f"[{row['date']}] {row['category']} | {row['expense_text']} | {row['amount']}")
            elif choice == '4':
                print("Goodbye!")
                break
            else:
                print("Invalid option.")

if __name__ == "__main__":
    app = SmartExpenseManager()
    app.run()
