import sqlite3
import tkinter as tk
from tkinter import messagebox
import datetime
import os

# Global variables to store time tracking state
is_counting = False
start_time = None
current_project_id = None

# Database file path (same folder as the script)
script_dir = os.path.join(os.environ['USERPROFILE'],"AppData\\Local")
db_file = os.path.join(script_dir, "projects.db")

def create_connection(db_file):
    """ Create a database connection to an SQLite database """
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        return conn
    except sqlite3.Error as e:
        print(f"Error: {e}")
    return conn

def create_table(conn, create_table_sql):
    """ Create a table using the provided SQL statement """
    try:
        c = conn.cursor()
        c.execute(create_table_sql)
    except sqlite3.Error as e:
        print(f"Error: {e}")

def setup_database():
    """ Create projects and time_entries tables if they do not exist """
    conn = create_connection(db_file)

    # SQL statement to create the projects table
    create_projects_table_sql = """
    CREATE TABLE IF NOT EXISTS projects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL
    );
    """
    
    # SQL statement to create the time_entries table
    create_time_entries_table_sql = """
    CREATE TABLE IF NOT EXISTS time_entries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER NOT NULL,
        start_time DATETIME NOT NULL,
        end_time DATETIME NOT NULL,
        duration REAL,  -- Duration in hours (fractional hours for minutes)
        FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
    );
    """

    # Create tables
    if conn is not None:
        create_table(conn, create_projects_table_sql)
        create_table(conn, create_time_entries_table_sql)
        conn.close()
    else:
        print("Error! Cannot create the database connection.")

def get_projects_with_total_time():
    """ Fetch all projects and their total time spent from the database """
    conn = create_connection(db_file)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT p.id, p.name, IFNULL(SUM(te.duration), 0) AS total_time
        FROM projects p
        LEFT JOIN time_entries te ON p.id = te.project_id
        GROUP BY p.id, p.name
    """)
    projects = cursor.fetchall()
    conn.close()
    return projects

def insert_time_entry(project_id, start_time, end_time, duration):
    """ Insert a new time entry for the project """
    conn = create_connection(db_file)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO time_entries (project_id, start_time, end_time, duration)
        VALUES (?, ?, ?, ?)
    """, (project_id, start_time, end_time, duration))
    conn.commit()
    conn.close()

def delete_project(project_id, project_listbox):
    """ Delete a project and its associated time entries """
    conn = create_connection(db_file)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM projects WHERE id = ?", (project_id,))
    conn.commit()
    conn.close()

    messagebox.showinfo("Success", "Project deleted successfully!")
    refresh_project_list(project_listbox)

def reset_time_spent(project_id, project_listbox):
    """ Reset time spent for a project by deleting its time entries """
    conn = create_connection(db_file)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM time_entries WHERE project_id = ?", (project_id,))
    conn.commit()
    conn.close()

    messagebox.showinfo("Success", "Time spent reset successfully!")
    refresh_project_list(project_listbox)

def add_project_to_db(name, add_project_window, project_listbox):
    """ Add a new project to the database """
    if not name.strip():
        messagebox.showwarning("Error", "Project name is required.")
        return

    conn = create_connection(db_file)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO projects (name) VALUES (?)", (name,))
    conn.commit()
    conn.close()

    messagebox.showinfo("Success", "Project added successfully!")
    add_project_window.destroy()
    
    # Refresh the project list after adding the project
    refresh_project_list(project_listbox)

def open_add_project_window(project_listbox):
    """ Open a sub-window to add a new project """
    add_project_window = tk.Toplevel()
    add_project_window.title("Add New Project")

    # Project name input
    name_label = tk.Label(add_project_window, text="Project Name:")
    name_label.pack(pady=5)
    name_entry = tk.Entry(add_project_window, width=40)
    name_entry.pack(pady=5)

    # Add project button
    add_button = tk.Button(add_project_window, text="Add Project", command=lambda: add_project_to_db(name_entry.get(), add_project_window, project_listbox))
    add_button.pack(pady=10)

def refresh_project_list(project_listbox):
    """ Refresh the project listbox with total time spent on each project """
    project_listbox.delete(0, tk.END)
    projects = get_projects_with_total_time()

    # Add each project to the listbox with total time spent
    for project in projects:
        project_listbox.insert(tk.END, f"{project[0]}: {project[1]} (Total Time: {project[2]:.2f} hours)")

def on_start_counting_click(project_listbox, status_label):
    """ Start counting time for the selected project """
    global is_counting, start_time, current_project_id
    
    if is_counting:
        messagebox.showwarning("Warning", "Time is already being counted for a project.")
        return

    selection = project_listbox.curselection()
    if not selection:
        messagebox.showwarning("Error", "Please select a project to start counting.")
        return
    
    selected_index = selection[0]
    project_info = project_listbox.get(selected_index)
    current_project_id = project_info.split(":")[0]  # Get project_id from selected text
    
    # Set the start time to now and change counting state
    start_time = datetime.datetime.now()
    is_counting = True

    # Update the status label
    status_label.config(text=f"Counting time for project {current_project_id}...")

def on_stop_counting_click(status_label, project_listbox):
    """ Stop counting time, calculate duration, and update the database """
    global is_counting, start_time, current_project_id
    
    if not is_counting:
        messagebox.showwarning("Warning", "No project is currently being counted.")
        return

    # End time is now
    end_time = datetime.datetime.now()

    # Calculate the duration in hours (fractional)
    duration = (end_time - start_time).total_seconds() / 3600

    # Insert the time entry into the database
    insert_time_entry(current_project_id, start_time, end_time, duration)

    # Reset counting state
    is_counting = False
    current_project_id = None
    start_time = None

    # Update the status label
    status_label.config(text="No project currently counting.")
    
    messagebox.showinfo("Success", f"Time for project updated successfully!")
    
    # Refresh the project list to reflect the updated time entries
    refresh_project_list(project_listbox)

def show_project_selection_gui():
    """ Create the GUI window to list projects and manage time tracking """
    root = tk.Tk()
    root.title("Project Time Tracker")

    # Create a Listbox widget to display projects
    project_listbox = tk.Listbox(root, width=50, height=10)
    project_listbox.pack(pady=20)

    # Populate the listbox with project names and total time spent
    refresh_project_list(project_listbox)

    # Status label to show whether time is counting
    status_label = tk.Label(root, text="No project currently counting.")
    status_label.pack(pady=10)

    # Create the "Start Counting" button
    start_button = tk.Button(root, text="Start Counting", command=lambda: on_start_counting_click(project_listbox, status_label))
    start_button.pack(pady=5)

    # Create the "Stop Counting" button
    stop_button = tk.Button(root, text="Stop Counting", command=lambda: on_stop_counting_click(status_label, project_listbox))
    stop_button.pack(pady=5)

    # Add Project button to open the sub-window
    add_project_button = tk.Button(root, text="Add Project", command=lambda: open_add_project_window(project_listbox))
    add_project_button.pack(pady=10)

    # Delete Project button
    delete_button = tk.Button(root, text="Delete Project", command=lambda: delete_selected_project(project_listbox))
    delete_button.pack(pady=5)

    # Reset Time button
    reset_button = tk.Button(root, text="Reset Time Spent", command=lambda: reset_selected_project_time(project_listbox))
    reset_button.pack(pady=5)

    # Run the GUI loop
    root.mainloop()

def delete_selected_project(project_listbox):
    """ Delete the selected project """
    selection = project_listbox.curselection()
    if not selection:
        messagebox.showwarning("Error", "Please select a project to delete.")
        return

    selected_index = selection[0]
    project_info = project_listbox.get(selected_index)
    project_id = project_info.split(":")[0]  # Get project_id from selected text

    if messagebox.askyesno("Confirm Deletion", "Are you sure you want to delete this project? This will also delete its time entries."):
        delete_project(project_id, project_listbox)

def reset_selected_project_time(project_listbox):
    """ Reset the time spent for the selected project """
    selection = project_listbox.curselection()
    if not selection:
        messagebox.showwarning("Error", "Please select a project to reset time spent.")
        return

    selected_index = selection[0]
    project_info = project_listbox.get(selected_index)
    project_id = project_info.split(":")[0]  # Get project_id from selected text

    if messagebox.askyesno("Confirm Reset", "Are you sure you want to reset the time spent for this project?"):
        reset_time_spent(project_id, project_listbox)

if __name__ == "__main__":
    # First, setup the database (create tables if they don't exist)
    setup_database()

    # Launch the GUI when the script starts
    show_project_selection_gui()
