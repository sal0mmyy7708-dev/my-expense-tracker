import json
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from pathlib import Path
from datetime import date, datetime
import hashlib
import hmac
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


PROJECT_DIR = Path(__file__).resolve().parent
EXPENSES_FILE = PROJECT_DIR / "expenses.json"
BUDGETS_FILE = PROJECT_DIR / "budgets.json"
PASSWORD_FILE = PROJECT_DIR / "password.json"


# ---------------- Password Functions ----------------

def password_hash(password):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def save_password(password):
    try:
        with PASSWORD_FILE.open("w", encoding="utf-8") as file:
            json.dump(
                {"password_hash": password_hash(password)},
                file,
                indent=2
            )
        return True
    except OSError as error:
        messagebox.showerror("Password Error", str(error))
        return False


def verify_password(password):
    try:
        with PASSWORD_FILE.open("r", encoding="utf-8") as file:
            saved = json.load(file)
    except (OSError, json.JSONDecodeError):
        messagebox.showerror(
            "Password Error",
            "Could not read password.json."
        )
        return False

    if not isinstance(saved, dict):
        return False

    saved_hash = saved.get("password_hash", "")

    return (
        isinstance(saved_hash, str)
        and bool(saved_hash)
        and hmac.compare_digest(
            password_hash(password), saved_hash
        )
    )


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
                messagebox.showwarning(
                    "Weak Password",
                    "Use at least 6 characters.",
                    parent=root
                )
                continue

            confirmation = simpledialog.askstring(
                "Confirm Password",
                "Enter the password again:",
                show="*",
                parent=root
            )

            if confirmation is None:
                return False

            if password != confirmation:
                messagebox.showerror(
                    "Password Mismatch",
                    "The passwords do not match.",
                    parent=root
                )
                continue

            return save_password(password)

    for attempt in range(3):
        password = simpledialog.askstring(
            "Login",
            f"Enter your password ({3 - attempt} attempts left):",
            show="*",
            parent=root
        )

        if password is None:
            return False

        if verify_password(password):
            return True

    messagebox.showerror(
        "Access Denied",
        "Too many failed attempts. The program will close.",
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
            "Incorrect Password",
            "The current password is incorrect.",
            parent=root
        )
        return

    while True:
        new_password = simpledialog.askstring(
            "Change Password",
            "Enter a new password (at least 6 characters):",
            show="*",
            parent=root
        )

        if new_password is None:
            return

        if len(new_password) < 6:
            messagebox.showwarning(
                "Weak Password",
                "Use at least 6 characters.",
                parent=root
            )
            continue

        if hmac.compare_digest(
            password_hash(current),
            password_hash(new_password)
        ):
            messagebox.showwarning(
                "Same Password",
                "Choose a different password.",
                parent=root
            )
            continue

        confirmation = simpledialog.askstring(
            "Confirm Password",
            "Enter the new password again:",
            show="*",
            parent=root
        )

        if confirmation is None:
            return

        if new_password != confirmation:
            messagebox.showerror(
                "Password Mismatch",
                "The passwords do not match. Try again.",
                parent=root
            )
            continue

        if save_password(new_password):
            messagebox.showinfo(
                "Password Changed",
                "Your password has been changed successfully.",
                parent=root
            )
        return


# ---------------- Data Helpers ----------------

def read_json(path, default):
    if not path.exists():
        return default

    try:
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)
    except (json.JSONDecodeError, OSError) as error:
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


# ---------------- Expense Tracker ----------------

class ExpenseTracker:
    def __init__(self, root):
        self.root = root
        self.root.title("My Expense Tracker")
        self.root.geometry("1100x730")
        self.root.minsize(850, 600)

        self.expenses = read_json(EXPENSES_FILE, [])
        self.budgets = read_json(BUDGETS_FILE, {})

        if not isinstance(self.expenses, list):
            messagebox.showerror(
                "Data Error",
                "expenses.json must contain a list."
            )
            self.expenses = []

        if not isinstance(self.budgets, dict):
            messagebox.showerror(
                "Data Error",
                "budgets.json must contain a dictionary."
            )
            self.budgets = {}

        self.selected_index = None
        self.build_ui()
        self.refresh_table()

    def build_ui(self):
        ttk.Label(
            self.root,
            text="My Expense Tracker",
            font=("Arial", 20, "bold")
        ).pack(pady=10)

        # Search and filters
        filters = ttk.LabelFrame(
            self.root, text="Search and Filters"
        )
        filters.pack(fill="x", padx=12, pady=5)

        ttk.Label(filters, text="Search:").grid(
            row=0, column=0, padx=5, pady=7
        )
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(
            filters, textvariable=self.search_var, width=18
        )
        search_entry.grid(row=0, column=1, padx=5, pady=7)
        search_entry.bind(
            "<KeyRelease>", lambda event: self.refresh_table()
        )

        ttk.Label(filters, text="Month (YYYY-MM):").grid(
            row=0, column=2, padx=5, pady=7
        )
        self.month_var = tk.StringVar()
        month_entry = ttk.Entry(
            filters, textvariable=self.month_var, width=12
        )
        month_entry.grid(row=0, column=3, padx=5, pady=7)
        month_entry.bind(
            "<KeyRelease>", lambda event: self.refresh_table()
        )

        ttk.Label(filters, text="Date (YYYY-MM-DD):").grid(
            row=0, column=4, padx=5, pady=7
        )
        self.date_var = tk.StringVar()
        date_entry = ttk.Entry(
            filters, textvariable=self.date_var, width=14
        )
        date_entry.grid(row=0, column=5, padx=5, pady=7)
        date_entry.bind(
            "<KeyRelease>", lambda event: self.refresh_table()
        )

        ttk.Button(
            filters, text="Show All", command=self.clear_filters
        ).grid(row=0, column=6, padx=5, pady=7)

        # Expenses table
        table_frame = ttk.Frame(self.root)
        table_frame.pack(
            fill="both", expand=True, padx=12, pady=5
        )

        columns = ("name", "category", "amount", "date")
        self.tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            height=12
        )

        self.tree.heading("name", text="Expense")
        self.tree.heading("category", text="Category")
        self.tree.heading("amount", text="Amount (EGP)")
        self.tree.heading("date", text="Date")

        self.tree.column("name", width=260)
        self.tree.column("category", width=150)
        self.tree.column("amount", width=140, anchor="center")
        self.tree.column("date", width=140, anchor="center")

        scrollbar = ttk.Scrollbar(
            table_frame,
            orient="vertical",
            command=self.tree.yview
        )
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.tree.bind(
            "<<TreeviewSelect>>", self.select_expense
        )

        # Expense form
        form = ttk.LabelFrame(
            self.root, text="Expense Details"
        )
        form.pack(fill="x", padx=12, pady=5)

        ttk.Label(form, text="Name:").grid(
            row=0, column=0, padx=5, pady=6
        )
        self.name_var = tk.StringVar()
        ttk.Entry(
            form, textvariable=self.name_var, width=18
        ).grid(row=0, column=1, padx=5, pady=6)

        ttk.Label(form, text="Category:").grid(
            row=0, column=2, padx=5, pady=6
        )
        self.category_var = tk.StringVar(value="Other")
        self.category_box = ttk.Combobox(
            form,
            textvariable=self.category_var,
            values=(
                "Food", "Transport", "Shopping", "Coffee",
                "Bills", "Health", "Education", "Other"
            ),
            width=15
        )
        self.category_box.grid(
            row=0, column=3, padx=5, pady=6
        )

        ttk.Label(form, text="Amount:").grid(
            row=0, column=4, padx=5, pady=6
        )
        self.amount_var = tk.StringVar()
        ttk.Entry(
            form, textvariable=self.amount_var, width=12
        ).grid(row=0, column=5, padx=5, pady=6)

        ttk.Label(form, text="Date (YYYY-MM-DD):").grid(
            row=1, column=0, padx=5, pady=6
        )
        self.expense_date_var = tk.StringVar(
            value=date.today().isoformat()
        )
        ttk.Entry(
            form, textvariable=self.expense_date_var, width=18
        ).grid(row=1, column=1, padx=5, pady=6)

        # Action buttons
        buttons = ttk.Frame(self.root)
        buttons.pack(fill="x", padx=12, pady=8)

        ttk.Button(
            buttons, text="Add Expense",
            command=self.add_expense
        ).pack(side="left", padx=3)

        ttk.Button(
            buttons, text="Update Selected",
            command=self.update_expense
        ).pack(side="left", padx=3)

        ttk.Button(
            buttons, text="Delete Selected",
            command=self.delete_expense
        ).pack(side="left", padx=3)

        ttk.Button(
            buttons, text="Monthly Report",
            command=self.monthly_report
        ).pack(side="left", padx=3)

        ttk.Button(
            buttons, text="Category Report",
            command=self.category_report
        ).pack(side="left", padx=3)

        ttk.Button(
            buttons, text="Show Charts",
            command=self.show_charts
        ).pack(side="left", padx=3)

        ttk.Button(
            buttons, text="Set Monthly Budget",
            command=self.set_budget
        ).pack(side="left", padx=3)

        # Password button on its own row
        security_buttons = ttk.Frame(self.root)
        security_buttons.pack(fill="x", padx=12, pady=(0, 8))

        ttk.Button(
            security_buttons,
            text="Change Password",
            command=lambda: change_password(self.root)
        ).pack(side="left", padx=3)

        self.status_var = tk.StringVar()
        ttk.Label(
            self.root,
            textvariable=self.status_var,
            relief="sunken"
        ).pack(fill="x", side="bottom")

    # ---------------- Save Data ----------------

    def save_expenses(self):
        try:
            with EXPENSES_FILE.open("w", encoding="utf-8") as file:
                json.dump(
                    self.expenses, file,
                    ensure_ascii=False, indent=2
                )
            return True
        except OSError as error:
            messagebox.showerror("Save Error", str(error))
            return False

    def save_budgets(self):
        try:
            with BUDGETS_FILE.open("w", encoding="utf-8") as file:
                json.dump(
                    self.budgets, file,
                    ensure_ascii=False, indent=2
                )
            return True
        except OSError as error:
            messagebox.showerror("Save Error", str(error))
            return False

    # ---------------- Search and Table ----------------

    def filtered_expenses(self):
        query = self.search_var.get().strip().lower()
        month = self.month_var.get().strip()
        chosen_date = self.date_var.get().strip()
        result = []

        for index, item in enumerate(self.expenses):
            name = expense_name(item).lower()
            category = expense_category(item).lower()
            amount_text = str(item.get("amount", "")).lower()
            item_date = expense_date(item)

            if query and not (
                query in name
                or query in category
                or query in amount_text
            ):
                continue

            if month and not item_date.startswith(month):
                continue

            if chosen_date and item_date != chosen_date:
                continue

            result.append((index, item))

        return result

    def refresh_table(self):
        for row in self.tree.get_children():
            self.tree.delete(row)

        visible = self.filtered_expenses()
        total = 0.0

        for index, item in visible:
            self.tree.insert(
                "", "end", iid=str(index),
                values=(
                    expense_name(item),
                    expense_category(item),
                    f"{expense_amount(item):.2f}",
                    expense_date(item)
                )
            )
            total += expense_amount(item)

        self.status_var.set(
            f"Showing {len(visible)} expenses | Total: {money(total)}"
        )

    def clear_filters(self):
        self.search_var.set("")
        self.month_var.set("")
        self.date_var.set("")
        self.refresh_table()

    def select_expense(self, event=None):
        selection = self.tree.selection()

        if not selection:
            self.selected_index = None
            return

        self.selected_index = int(selection[0])
        item = self.expenses[self.selected_index]

        self.name_var.set(expense_name(item))
        self.category_var.set(expense_category(item))
        self.amount_var.set(str(item.get("amount", "")))
        self.expense_date_var.set(expense_date(item))

    # ---------------- Expense Form ----------------

    def get_form_values(self):
        name = self.name_var.get().strip()
        category = self.category_var.get().strip() or "Other"
        amount_text = self.amount_var.get().strip()
        chosen_date = self.expense_date_var.get().strip()

        if not name:
            messagebox.showwarning(
                "Missing Name", "Enter an expense name."
            )
            return None

        try:
            amount = float(amount_text)
            if amount < 0:
                raise ValueError
        except ValueError:
            messagebox.showwarning(
                "Invalid Amount",
                "Enter a valid amount of 0 or more."
            )
            return None

        try:
            datetime.strptime(chosen_date, "%Y-%m-%d")
        except ValueError:
            messagebox.showwarning(
                "Invalid Date", "Use YYYY-MM-DD."
            )
            return None

        return name, category, amount, chosen_date

    def add_expense(self):
        values = self.get_form_values()
        if values is None:
            return

        name, category, amount, chosen_date = values
        self.expenses.append({
            "name": name,
            "category": category,
            "amount": amount,
            "date": chosen_date
        })

        if self.save_expenses():
            self.clear_form()
            self.refresh_table()

    def update_expense(self):
        if self.selected_index is None:
            messagebox.showinfo(
                "Select Expense",
                "Select an expense from the table first."
            )
            return

        values = self.get_form_values()
        if values is None:
            return

        name, category, amount, chosen_date = values
        item = self.expenses[self.selected_index]

        if "name" in item or "description" not in item:
            item["name"] = name
        else:
            item["description"] = name

        item["category"] = category
        item["amount"] = amount
        item["date"] = chosen_date

        if self.save_expenses():
            self.clear_form()
            self.refresh_table()

    def delete_expense(self):
        if self.selected_index is None:
            messagebox.showinfo(
                "Select Expense",
                "Select an expense from the table first."
            )
            return

        if not messagebox.askyesno(
            "Confirm Deletion",
            "Delete the selected expense?"
        ):
            return

        del self.expenses[self.selected_index]

        if self.save_expenses():
            self.selected_index = None
            self.clear_form()
            self.refresh_table()

    def clear_form(self):
        self.selected_index = None
        self.name_var.set("")
        self.category_var.set("Other")
        self.amount_var.set("")
        self.expense_date_var.set(date.today().isoformat())

        for selected in self.tree.selection():
            self.tree.selection_remove(selected)

    # ---------------- Reports ----------------

    def monthly_expenses(self, month):
        return [
            item for item in self.expenses
            if expense_date(item).startswith(month)
        ]

    def monthly_report(self):
        month = self.month_var.get().strip()

        if not month:
            month = date.today().strftime("%Y-%m")

        try:
            datetime.strptime(month, "%Y-%m")
        except ValueError:
            messagebox.showwarning(
                "Invalid Month", "Use YYYY-MM."
            )
            return

        items = self.monthly_expenses(month)
        total = sum(expense_amount(item) for item in items)
        budget = self.budgets.get(month)

        report = f"Monthly Report: {month}\n\n"
        report += f"Number of expenses: {len(items)}\n"
        report += f"Total spent: {money(total)}\n"

        if budget is not None:
            remaining = float(budget) - total
            report += f"Budget: {money(budget)}\n"
            report += f"Remaining: {money(remaining)}\n"

            if remaining < 0:
                report += "\nWarning: You are over budget!"

        messagebox.showinfo("Monthly Report", report)

    def filtered_items_for_report(self):
        return [item for _, item in self.filtered_expenses()]

    def category_report(self):
        totals = {}

        for item in self.filtered_items_for_report():
            category = expense_category(item)
            totals[category] = (
                totals.get(category, 0) + expense_amount(item)
            )

        if not totals:
            messagebox.showinfo(
                "Category Report", "No expenses to report."
            )
            return

        lines = ["Spending by category:\n"]

        for category, total in sorted(
            totals.items(),
            key=lambda pair: pair[1],
            reverse=True
        ):
            lines.append(f"{category}: {money(total)}")

        messagebox.showinfo(
            "Category Report", "\n".join(lines)
        )

    # ---------------- Monthly Budget ----------------

    def set_budget(self):
        month = self.month_var.get().strip()

        if not month:
            month = date.today().strftime("%Y-%m")

        try:
            datetime.strptime(month, "%Y-%m")
        except ValueError:
            messagebox.showwarning(
                "Invalid Month", "Use YYYY-MM."
            )
            return

        current = self.budgets.get(month, "")

        try:
            initial = float(current) if current != "" else None
        except (ValueError, TypeError):
            initial = None

        amount = simpledialog.askfloat(
            "Monthly Budget",
            f"Enter budget for {month} (EGP):",
            initialvalue=initial,
            minvalue=0,
            parent=self.root
        )

        if amount is None:
            return

        self.budgets[month] = amount

        if self.save_budgets():
            total = sum(
                expense_amount(item)
                for item in self.monthly_expenses(month)
            )

            report = (
                f"Budget for {month}: {money(amount)}\n"
                f"Spent so far: {money(total)}"
            )

            if total > amount:
                report += "\nWarning: You are over budget!"

            messagebox.showinfo("Budget Saved", report)

    # ---------------- Charts ----------------

    def show_charts(self):
        items = self.filtered_items_for_report()

        if not items:
            messagebox.showinfo(
                "No Data",
                "There are no expenses matching the current filters."
            )
            return

        category_totals = {}
        daily_totals = {}

        for item in items:
            amount = expense_amount(item)
            category = expense_category(item)

            category_totals[category] = (
                category_totals.get(category, 0) + amount
            )

            item_date = expense_date(item)
            if item_date:
                daily_totals[item_date] = (
                    daily_totals.get(item_date, 0) + amount
                )

        chart_window = tk.Toplevel(self.root)
        chart_window.title("Expense Charts")
        chart_window.geometry("1100x650")

        figure, axes = plt.subplots(1, 2, figsize=(12, 5))
        figure.suptitle("Expense Summary")

        positive_categories = {
            name: total
            for name, total in category_totals.items()
            if total > 0
        }

        if positive_categories:
            axes[0].pie(
                list(positive_categories.values()),
                labels=list(positive_categories.keys()),
                autopct="%1.1f%%"
            )
        else:
            axes[0].text(
                0.5, 0.5, "No positive amounts",
                ha="center", va="center"
            )

        axes[0].set_title("Spending by Category")

        dates = sorted(daily_totals)
        amounts = [daily_totals[item_date] for item_date in dates]

        if dates and any(amount > 0 for amount in amounts):
            positions = list(range(len(dates)))

            axes[1].bar(
                positions, amounts,
                width=0.7, color="steelblue"
            )
            axes[1].set_title("Spending by Date")
            axes[1].set_xlabel("Date")
            axes[1].set_ylabel("Amount (EGP)")

            step = max(1, (len(dates) + 9) // 10)
            shown_positions = positions[::step]

            axes[1].set_xticks(shown_positions)
            axes[1].set_xticklabels(
                [dates[i] for i in shown_positions],
                rotation=45, ha="right"
            )

            axes[1].grid(axis="y", alpha=0.3)
            axes[1].margins(x=0.05)
            axes[1].set_ylim(bottom=0)
        else:
            axes[1].text(
                0.5, 0.5,
                "No dated expenses with positive amounts",
                ha="center", va="center", wrap=True
            )
            axes[1].set_title("Spending by Date")

        figure.tight_layout()

        canvas = FigureCanvasTkAgg(
            figure, master=chart_window
        )
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

        def close_chart():
            plt.close(figure)
            chart_window.destroy()

        chart_window.protocol(
            "WM_DELETE_WINDOW", close_chart
        )


# ---------------- Start Program ----------------

if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()

    if login_or_setup(root):
        root.deiconify()
        app = ExpenseTracker(root)
        root.mainloop()
    else:
        root.destroy()
