import json
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from pathlib import Path
from datetime import date, datetime
import hashlib
import hmac
import secrets
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


PROJECT_DIR = Path(__file__).resolve().parent
EXPENSES_FILE = PROJECT_DIR / "expenses.json"
BUDGETS_FILE = PROJECT_DIR / "budgets.json"
PASSWORD_FILE = PROJECT_DIR / "password.json"


# ---------- Password security ----------

def password_hash(password):
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=2**14,
        r=8,
        p=1,
        dklen=32
    )
    return {
        "algorithm": "scrypt",
        "salt": salt.hex(),
        "password_hash": digest.hex()
    }


def save_password(password):
    try:
        data = password_hash(password)
        PASSWORD_FILE.write_text(
            json.dumps(data, indent=2),
            encoding="utf-8"
        )
        return True
    except (OSError, ValueError) as error:
        messagebox.showerror(
            "Error",
            f"Could not save password:\n{error}"
        )
        return False


def verify_password(password):
    try:
        data = json.loads(PASSWORD_FILE.read_text(encoding="utf-8"))

        if not isinstance(data, dict):
            return False

        # New password format: salted scrypt
        if data.get("algorithm") == "scrypt":
            salt = bytes.fromhex(data["salt"])
            expected = data["password_hash"]

            actual = hashlib.scrypt(
                password.encode("utf-8"),
                salt=salt,
                n=2**14,
                r=8,
                p=1,
                dklen=32
            ).hex()

            return hmac.compare_digest(actual, expected)

        # Old format: SHA-256, for compatibility
        old_hash = data.get("password_hash")

        if isinstance(old_hash, str):
            old_actual = hashlib.sha256(
                password.encode("utf-8")
            ).hexdigest()

            if hmac.compare_digest(old_actual, old_hash):
                # Upgrade the saved password format after successful login.
                save_password(password)
                return True

        return False

    except (OSError, ValueError, KeyError, TypeError):
        return False


def login_or_setup(root):
    if not PASSWORD_FILE.exists():
        while True:
            password = simpledialog.askstring(
                "Create Password",
                "Create a password (at least 6 characters):",
                show="*",
                parent=root
            )

            if password is None:
                return False

            if len(password) < 6:
                messagebox.showerror(
                    "Error",
                    "Password must be at least 6 characters.",
                    parent=root
                )
                continue

            confirm = simpledialog.askstring(
                "Confirm Password",
                "Enter your password again:",
                show="*",
                parent=root
            )

            if confirm is None:
                return False

            if password != confirm:
                messagebox.showerror(
                    "Error",
                    "Passwords do not match.",
                    parent=root
                )
                continue

            if save_password(password):
                messagebox.showinfo(
                    "Success",
                    "Password created successfully.",
                    parent=root
                )
                return True

            return False

    for _ in range(3):
        password = simpledialog.askstring(
            "Login",
            "Enter your password:",
            show="*",
            parent=root
        )

        if password is None:
            return False

        if verify_password(password):
            return True

        messagebox.showerror(
            "Error",
            "Incorrect password.",
            parent=root
        )

    messagebox.showerror(
        "Login Failed",
        "Too many incorrect attempts.",
        parent=root
    )
    return False


def change_password(root):
    current = simpledialog.askstring(
        "Change Password",
        "Enter your current password:",
        show="*",
        parent=root
    )

    if current is None:
        return

    if not verify_password(current):
        messagebox.showerror(
            "Error",
            "Current password is incorrect.",
            parent=root
        )
        return

    new_password = simpledialog.askstring(
        "Change Password",
        "Enter a new password (at least 6 characters):",
        show="*",
        parent=root
    )

    if new_password is None:
        return

    if len(new_password) < 6:
        messagebox.showerror(
            "Error",
            "Password must be at least 6 characters.",
            parent=root
        )
        return

    if new_password == current:
        messagebox.showerror(
            "Error",
            "New password must be different.",
            parent=root
        )
        return

    confirm = simpledialog.askstring(
        "Change Password",
        "Confirm your new password:",
        show="*",
        parent=root
    )

    if confirm is None:
        return

    if new_password != confirm:
        messagebox.showerror(
            "Error",
            "Passwords do not match.",
            parent=root
        )
        return

    if save_password(new_password):
        messagebox.showinfo(
            "Success",
            "Password changed successfully.",
            parent=root
        )


# ---------- Data helpers ----------

def read_json(path, default):
    if not path.exists():
        return default

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        messagebox.showerror(
            "File Error",
            f"Could not read {path.name}:\n{error}"
        )
        return default


def money(value):
    try:
        return f"{float(value):.2f} EGP"
    except (ValueError, TypeError):
        return "0.00 EGP"


def expense_name(item):
    return str(item.get("name", item.get("description", "")))


def expense_date(item):
    return str(item.get("date", ""))


def expense_amount(item):
    try:
        return float(item.get("amount", 0))
    except (ValueError, TypeError):
        return 0.0


def expense_category(item):
    return str(item.get("category", "Other"))


# ---------- Main application ----------

class ExpenseTracker:
    def __init__(self, root):
        self.root = root
        self.root.title("My Expense Tracker")
        self.root.geometry("1100x730")
        self.root.minsize(850, 600)

        self.expenses = read_json(EXPENSES_FILE, [])
        self.budgets = read_json(BUDGETS_FILE, {})

        if not isinstance(self.expenses, list):
            self.expenses = []

        if not isinstance(self.budgets, dict):
            self.budgets = {}

        self.build_ui()
        self.refresh_table()


    def build_ui(self):
        # Search and filters
        filter_frame = ttk.LabelFrame(
            self.root, text="Search and Filters", padding=10
        )
        filter_frame.pack(fill="x", padx=10, pady=5)

        ttk.Label(filter_frame, text="Search:").grid(
            row=0, column=0, padx=5, pady=5
        )
        self.search_var = tk.StringVar()
        ttk.Entry(
            filter_frame, textvariable=self.search_var, width=22
        ).grid(row=0, column=1, padx=5)

        ttk.Label(filter_frame, text="Month (YYYY-MM):").grid(
            row=0, column=2, padx=5
        )
        self.month_filter_var = tk.StringVar()
        ttk.Entry(
            filter_frame, textvariable=self.month_filter_var, width=12
        ).grid(row=0, column=3, padx=5)

        ttk.Label(filter_frame, text="Date (YYYY-MM-DD):").grid(
            row=0, column=4, padx=5
        )
        self.date_filter_var = tk.StringVar()
        ttk.Entry(
            filter_frame, textvariable=self.date_filter_var, width=14
        ).grid(row=0, column=5, padx=5)

        ttk.Button(
            filter_frame, text="Search", command=self.refresh_table
        ).grid(row=0, column=6, padx=5)

        ttk.Button(
            filter_frame, text="Show All", command=self.clear_filters
        ).grid(row=0, column=7, padx=5)

        # Expenses table
        table_frame = ttk.Frame(self.root)
        table_frame.pack(fill="both", expand=True, padx=10, pady=5)

        columns = ("name", "category", "amount", "date")
        self.tree = ttk.Treeview(
            table_frame, columns=columns, show="headings", height=12
        )

        self.tree.heading("name", text="Expense Name")
        self.tree.heading("category", text="Category")
        self.tree.heading("amount", text="Amount")
        self.tree.heading("date", text="Date")

        self.tree.column("name", width=300)
        self.tree.column("category", width=160)
        self.tree.column("amount", width=150, anchor="center")
        self.tree.column("date", width=140, anchor="center")

        scrollbar = ttk.Scrollbar(
            table_frame, orient="vertical", command=self.tree.yview
        )
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.tree.bind(
            "<<TreeviewSelect>>", self.select_expense
        )

        # Expense form
        form = ttk.LabelFrame(
            self.root, text="Expense Details", padding=10
        )
        form.pack(fill="x", padx=10, pady=5)

        ttk.Label(form, text="Name:").grid(
            row=0, column=0, padx=5, pady=5, sticky="w"
        )
        self.name_var = tk.StringVar()
        ttk.Entry(
            form, textvariable=self.name_var, width=25
        ).grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(form, text="Category:").grid(
            row=0, column=2, padx=5, pady=5, sticky="w"
        )
        self.category_var = tk.StringVar(value="Other")
        self.category_box = ttk.Combobox(
            form,
            textvariable=self.category_var,
            values=[
                "Food", "Transport", "Shopping", "Coffee",
                "Bills", "Health", "Education", "Other"
            ],
            state="readonly",
            width=18
        )
        self.category_box.grid(row=0, column=3, padx=5, pady=5)

        ttk.Label(form, text="Amount (EGP):").grid(
            row=1, column=0, padx=5, pady=5, sticky="w"
        )
        self.amount_var = tk.StringVar()
        ttk.Entry(
            form, textvariable=self.amount_var, width=25
        ).grid(row=1, column=1, padx=5, pady=5)

        ttk.Label(form, text="Date (YYYY-MM-DD):").grid(
            row=1, column=2, padx=5, pady=5, sticky="w"
        )
        self.expense_date_var = tk.StringVar(
            value=date.today().isoformat()
        )
        ttk.Entry(
            form, textvariable=self.expense_date_var, width=21
        ).grid(row=1, column=3, padx=5, pady=5)

        # Action buttons
        actions = ttk.Frame(self.root, padding=5)
        actions.pack(fill="x", padx=10)

        ttk.Button(
            actions, text="Add Expense", command=self.add_expense
        ).pack(side="left", padx=3)

        ttk.Button(
            actions, text="Update Selected",
            command=self.update_expense
        ).pack(side="left", padx=3)

        ttk.Button(
            actions, text="Delete Selected",
            command=self.delete_expense
        ).pack(side="left", padx=3)

        ttk.Button(
            actions, text="Monthly Report",
            command=self.monthly_report
        ).pack(side="left", padx=3)

        ttk.Button(
            actions, text="Category Report",
            command=self.category_report
        ).pack(side="left", padx=3)

        ttk.Button(
            actions, text="Show Charts",
            command=self.show_charts
        ).pack(side="left", padx=3)

        ttk.Button(
            actions, text="Set Monthly Budget",
            command=self.set_monthly_budget
        ).pack(side="left", padx=3)

        ttk.Button(
            actions, text="Change Password",
            command=lambda: change_password(self.root)
        ).pack(side="right", padx=3)

        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(
            self.root, textvariable=self.status_var,
            relief="sunken", anchor="w"
        ).pack(fill="x", side="bottom")

    # ---------- Save data ----------

    def save_expenses(self):
        try:
            EXPENSES_FILE.write_text(
                json.dumps(
                    self.expenses, ensure_ascii=False, indent=2
                ),
                encoding="utf-8"
            )
            return True
        except OSError as error:
            messagebox.showerror(
                "Error", f"Could not save expenses:\n{error}"
            )
            return False

    def save_budgets(self):
        try:
            BUDGETS_FILE.write_text(
                json.dumps(
                    self.budgets, ensure_ascii=False, indent=2
                ),
                encoding="utf-8"
            )
            return True
        except OSError as error:
            messagebox.showerror(
                "Error", f"Could not save budgets:\n{error}"
            )
            return False

    # ---------- Table and filters ----------

    def refresh_table(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        search = self.search_var.get().strip().lower()
        month = self.month_filter_var.get().strip()
        selected_date = self.date_filter_var.get().strip()

        for index, expense in enumerate(self.expenses):
            name = expense_name(expense)
            category = expense_category(expense)
            amount = expense_amount(expense)
            expense_day = expense_date(expense)

            if search and search not in (
                name + " " + category
            ).lower():
                continue

            if month and not expense_day.startswith(month):
                continue

            if selected_date and expense_day != selected_date:
                continue

            self.tree.insert(
                "",
                "end",
                iid=str(index),
                values=(
                    name, category, money(amount), expense_day
                )
            )

        self.status_var.set(
            f"Showing {len(self.tree.get_children())} expense(s)"
        )

    def clear_filters(self):
        self.search_var.set("")
        self.month_filter_var.set("")
        self.date_filter_var.set("")
        self.refresh_table()

    def select_expense(self, _event=None):
        selection = self.tree.selection()
        if not selection:
            return

        try:
            index = int(selection[0])
            expense = self.expenses[index]
        except (ValueError, IndexError):
            return

        self.name_var.set(expense_name(expense))
        self.category_var.set(expense_category(expense))
        self.amount_var.set(str(expense_amount(expense)))
        self.expense_date_var.set(expense_date(expense))

    # ---------- Validate and manage expenses ----------

    def get_form_data(self):
        name = self.name_var.get().strip()
        category = self.category_var.get().strip() or "Other"
        amount_text = self.amount_var.get().strip()
        expense_day = self.expense_date_var.get().strip()

        if not name:
            messagebox.showerror(
                "Invalid Input", "Please enter an expense name."
            )
            return None

        try:
            amount = float(amount_text)
            if amount <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror(
                "Invalid Input",
                "Amount must be a number greater than zero."
            )
            return None

        try:
            datetime.strptime(expense_day, "%Y-%m-%d")
        except ValueError:
            messagebox.showerror(
                "Invalid Date",
                "Enter the date as YYYY-MM-DD."
            )
            return None

        return {
            "name": name,
            "category": category,
            "amount": amount,
            "date": expense_day
        }

    def clear_form(self):
        self.name_var.set("")
        self.category_var.set("Other")
        self.amount_var.set("")
        self.expense_date_var.set(date.today().isoformat())

        for item in self.tree.selection():
            self.tree.selection_remove(item)

    def add_expense(self):
        expense = self.get_form_data()
        if expense is None:
            return

        self.expenses.append(expense)

        if self.save_expenses():
            self.refresh_table()
            self.clear_form()
            self.status_var.set("Expense added successfully.")

    def update_expense(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning(
                "Select Expense",
                "Please select an expense to update."
            )
            return

        expense = self.get_form_data()
        if expense is None:
            return

        index = int(selection[0])
        self.expenses[index] = expense

        if self.save_expenses():
            self.refresh_table()
            self.clear_form()
            self.status_var.set("Expense updated successfully.")

    def delete_expense(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning(
                "Select Expense",
                "Please select an expense to delete."
            )
            return

        if not messagebox.askyesno(
            "Confirm Delete",
            "Are you sure you want to delete the selected expense?"
        ):
            return

        index = int(selection[0])
        del self.expenses[index]

        if self.save_expenses():
            self.refresh_table()
            self.clear_form()
            self.status_var.set("Expense deleted successfully.")

    # ---------- Reports ----------

    def get_month_expenses(self, month):
        return [
            expense for expense in self.expenses
            if expense_date(expense).startswith(month)
        ]

    def monthly_report(self):
        month = self.month_filter_var.get().strip()

        if not month:
            month = date.today().strftime("%Y-%m")

        try:
            datetime.strptime(month, "%Y-%m")
        except ValueError:
            messagebox.showerror(
                "Invalid Month",
                "Enter the month as YYYY-MM."
            )
            return

        expenses = self.get_month_expenses(month)
        total = sum(expense_amount(item) for item in expenses)

        budget = self.budgets.get(month)
        report = (
            f"Monthly Report: {month}\n\n"
            f"Number of expenses: {len(expenses)}\n"
            f"Total spending: {money(total)}"
        )

        if budget is not None:
            report += (
                f"\nMonthly budget: {money(budget)}"
                f"\nRemaining budget: {money(budget - total)}"
            )

        messagebox.showinfo("Monthly Report", report)

    def category_report(self):
        month = self.month_filter_var.get().strip()

        if not month:
            month = date.today().strftime("%Y-%m")

        expenses = self.get_month_expenses(month)
        totals = {}

        for expense in expenses:
            category = expense_category(expense)
            totals[category] = (
                totals.get(category, 0) + expense_amount(expense)
            )

        if not totals:
            messagebox.showinfo(
                "Category Report",
                f"No expenses found for {month}."
            )
            return

        report = f"Category Report: {month}\n\n"
        for category, total in sorted(
            totals.items(), key=lambda item: item[1], reverse=True
        ):
            report += f"{category}: {money(total)}\n"

        report += (
            f"\nTotal: {money(sum(totals.values()))}"
        )
        messagebox.showinfo("Category Report", report)

    # ---------- Monthly budget ----------

    def set_monthly_budget(self):
        month = simpledialog.askstring(
            "Monthly Budget",
            "Enter month (YYYY-MM):",
            initialvalue=date.today().strftime("%Y-%m"),
            parent=self.root
        )

        if month is None:
            return

        month = month.strip()

        try:
            datetime.strptime(month, "%Y-%m")
        except ValueError:
            messagebox.showerror(
                "Invalid Month", "Enter the month as YYYY-MM."
            )
            return

        amount = simpledialog.askfloat(
            "Monthly Budget",
            f"Enter the budget for {month} (EGP):",
            minvalue=0.01,
            parent=self.root
        )

        if amount is None:
            return

        old_budget = self.budgets.get(month)
        self.budgets[month] = amount

        if not self.save_budgets():
            if old_budget is None:
                self.budgets.pop(month, None)
            else:
                self.budgets[month] = old_budget
            return

        total = sum(
            expense_amount(item)
            for item in self.get_month_expenses(month)
        )

        if total > amount:
            messagebox.showwarning(
                "Budget Exceeded",
                f"You have spent {money(total)} in {month}.\n"
                f"Your budget is {money(amount)}."
            )
        else:
            messagebox.showinfo(
                "Budget Saved",
                f"Budget for {month}: {money(amount)}\n"
                f"Remaining: {money(amount - total)}"
            )

    # ---------- Charts ----------

    def show_charts(self):
        month = self.month_filter_var.get().strip()

        if not month:
            month = date.today().strftime("%Y-%m")

        expenses = self.get_month_expenses(month)

        if not expenses:
            messagebox.showinfo(
                "Charts", f"No expenses found for {month}."
            )
            return

        category_totals = {}
        daily_totals = {}

        for expense in expenses:
            category = expense_category(expense)
            amount = expense_amount(expense)
            expense_day = expense_date(expense)

            category_totals[category] = (
                category_totals.get(category, 0) + amount
            )
            daily_totals[expense_day] = (
                daily_totals.get(expense_day, 0) + amount
            )

        chart_window = tk.Toplevel(self.root)
        chart_window.title(f"Expense Charts - {month}")
        chart_window.geometry("1000x500")

        figure, axes = plt.subplots(1, 2, figsize=(10, 4.5))

        axes[0].pie(
            list(category_totals.values()),
            labels=list(category_totals.keys()),
            autopct="%1.1f%%"
        )
        axes[0].set_title("Spending by Category")

        days = sorted(daily_totals.keys())
        axes[1].bar(
            days, [daily_totals[day] for day in days]
        )
        axes[1].set_title("Daily Spending")
        axes[1].set_ylabel("Amount (EGP)")
        axes[1].tick_params(axis="x", rotation=45)

        figure.tight_layout()

        canvas = FigureCanvasTkAgg(
            figure, master=chart_window
        )
        canvas.draw()
        canvas.get_tk_widget().pack(
            fill="both", expand=True
        )

        def close_charts():
            plt.close(figure)
            chart_window.destroy()

        chart_window.protocol("WM_DELETE_WINDOW", close_charts)


# ---------- Start application ----------

if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()

    if login_or_setup(root):
        root.deiconify()
        app = ExpenseTracker(root)
        root.mainloop()
    else:
        root.destroy()
