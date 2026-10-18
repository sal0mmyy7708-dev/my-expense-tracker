# My Expense Tracker

A Python-based desktop application for tracking personal expenses, managing monthly budgets, and visualizing spending habits.

## Overview

My Expense Tracker is a desktop application developed with Python to help users organize their expenses and monitor their spending. It provides a graphical interface for managing expense records, reviewing monthly reports, and tracking spending by category.

This project was created as part of my journey in learning Python programming and building practical software applications.

## Application Screenshot

![My Expense Tracker Screenshot](Screenshot%202026-10-18%20231024.png)

## Features

- **Expense Management:** Add, edit, and delete expense records.
- **Search and Filtering:** Find expenses and filter records.
- **Monthly Reports:** Review expenses over a monthly period.
- **Category Tracking:** View expenses grouped by category.
- **Budget Management:** Set and monitor a monthly budget.
- **Data Visualization:** Display charts to better understand spending patterns.
- **Password Protection:** Protect access to the application with a password.
- **Local Data Storage:** Store application data in local JSON files.

## Technologies Used

- **Python 3** — Application logic and functionality.
- **Tkinter** — Graphical user interface (GUI).
- **Matplotlib** — Expense charts and data visualization.
- **JSON** — Local data storage.
- **Hashlib** — Password hashing.

## Getting Started

### Prerequisites

- Python 3 installed on your computer.
- Matplotlib installed in your Python environment.

### Installation

1. Clone or download this repository.
2. Open a terminal in the project folder.
3. Install Matplotlib:

   ```bash
   pip install matplotlib
   ```

### Run the Application

Run the following command from the project folder:

```bash
python expense_tracker_gui_new.py
```

## Project Structure

```text
my-expense-tracker/
├── expense_tracker_gui_new.py
├── README.md
└── .gitignore
```

*Note: The project structure above shows the main application and documentation files. Other local files may exist.*

## Security and Data Privacy

- Expense and budget data are stored locally in JSON files.
- Password verification uses password hashing.
- Local data files should not be committed to a public repository.
- The `.gitignore` file helps prevent specified local data files from being tracked by Git.

**Important:** Password protection does not encrypt expense or budget JSON files. Keep sensitive data out of the repository.

## Learning Goals

Through this project, I practiced:

- Writing Python programs and organizing application logic.
- Building desktop interfaces with Tkinter.
- Working with files and JSON data.
- Using Matplotlib for data visualization.
- Implementing password hashing.
- Managing project files with GitHub.

## Future Improvements

- Export expense reports to CSV or Excel.
- Add more advanced reporting and filtering options.
- Improve the user interface and usability.
- Add automated tests.

## Author

Created as a personal learning project while developing my Python programming skills.
