import mysql.connector
from mysql.connector import errorcode
import datetime

# --- Helper Functions for your Event Database ---

def list_available_venues(cursor):
    """Fetches and prints all venues marked as available."""
    print("\n--- 🏟️ Available Venues ---")
    try:
        cursor.execute("SELECT id, name, building, capacity FROM tbl_venues WHERE is_available = 1 ORDER BY capacity DESC")
        venues = cursor.fetchall()
        
        if not venues:
            print("No available venues found.")
            return
            
        print(f"{'ID':<5} | {'Name':<25} | {'Building':<15} | {'Capacity':<10}")
        print("-" * 60)
        for row in venues:
            # row[0]=id, row[1]=name, row[2]=building, row[3]=capacity
            print(f"{row[0]:<5} | {row[1]:<25} | {row[2]:<15} | {row[3]:<10}")
            
    except mysql.connector.Error as err:
        print(f"Error listing venues: {err}")

def list_scheduled_events(cursor):
    """Fetches and prints all events that are 'Scheduled'."""
    print("\n--- 🗓️ Scheduled Events ---")
    
    # This query joins events with venues and hosts to show names instead of just IDs
    query = """
        SELECT 
            e.id, 
            e.name, 
            e.date, 
            e.start_time, 
            v.name AS venue_name, 
            h.name AS host_name
        FROM tbl_events e
        LEFT JOIN tbl_venues v ON e.location_id = v.id
        JOIN tbl_hosts h ON e.organizer_id = h.id
        WHERE e.status = 'Scheduled'
        ORDER BY e.date, e.start_time
    """
    try:
        cursor.execute(query)
        events = cursor.fetchall()
        
        if not events:
            print("No scheduled events found.")
            return
            
        print(f"{'ID':<5} | {'Event Name':<25} | {'Date':<12} | {'Start':<10} | {'Venue':<20} | {'Host':<20}")
        print("-" * 95)
        for row in events:
            # row[0]=id, row[1]=name, row[2]=date, row[3]=start_time, row[4]=venue_name, row[5]=host_name
            print(f"{row[0]:<5} | {row[1]:<25} | {str(row[2]):<12} | {str(row[3]):<10} | {row[4] or 'N/A':<20} | {row[5]:<20}")
        return True # Return True if events exist, to help other functions
        
    except mysql.connector.Error as err:
        print(f"Error listing events: {err}")
        return False

def add_new_student(cursor, conn):
    """Inserts a new student into tbl_students."""
    print("\n--- 🧑‍🎓 Add New Student ---")
    try:
        srn = input("Enter SRN (e.g., PES2UG23CS001): ")
        name = input("Enter student name: ")
        semester = int(input("Enter semester (1-8): "))
        section = input("Enter section (e.g., A): ")

        if not (1 <= semester <= 8):
            print("Invalid semester. Must be between 1 and 8.")
            return

        sql = "INSERT INTO tbl_students (srn, name, semester, section) VALUES (%s, %s, %s, %s)"
        val = (srn, name, semester, section)
        
        cursor.execute(sql, val)
        conn.commit() # Commit the transaction
        
        print(f"✅ Successfully added student: {name} ({srn})")
        
    except mysql.connector.Error as err:
        conn.rollback() # Rollback changes on error
        if err.errno == 1062: # Duplicate entry
            print(f"Error: A student with SRN '{srn}' already exists.")
        else:
            print(f"Failed to add student: {err}")
    except ValueError:
        print("Invalid input. Semester must be a number.")

def register_student_for_event(cursor, conn):
    """Inserts a record into tbl_event_participants."""
    print("\n--- 🎟️ Register Student for Event ---")
    
    # Show available events
    if not list_scheduled_events(cursor):
        return # Stop if no events to register for
    
    try:
        event_id = int(input("\nEnter the Event ID to register for: "))
        
        # List students to help the user find the ID
        print("\n--- Student List ---")
        cursor.execute("SELECT id, srn, name FROM tbl_students")
        students = cursor.fetchall()
        for row in students:
            print(f"ID: {row[0]}, SRN: {row[1]}, Name: {row[2]}")
        
        user_id = int(input("\nEnter the Student ID to register: "))
        
        sql = "INSERT INTO tbl_event_participants (event_id, user_id, registration_time) VALUES (%s, %s, %s)"
        val = (event_id, user_id, datetime.datetime.now())
        
        cursor.execute(sql, val)
        conn.commit()
        
        print(f"✅Successfully registered student {user_id} for event {event_id}.")
        
    except mysql.connector.Error as err:
        conn.rollback()
        if err.errno == 1062: # Duplicate key
            print("Error: This student is already registered for this event.")
        elif err.errno == 1452: # Foreign key constraint fails
             print("Error: Invalid Student ID or Event ID. Please check and try again.")
        else:
            print(f"Failed to register: {err}")
    except ValueError:
        print("Invalid input. IDs must be numbers.")

def show_event_feedback(cursor):
    """Generates a report of feedback for a specific event."""
    print("\n--- 📊 View Event Feedback ---")
    
    # Re-use the list_scheduled_events function
    cursor.execute("SELECT id, name FROM tbl_events")
    print("--- All Events ---")
    for row in cursor.fetchall():
        print(f"ID: {row[0]}, Name: {row[1]}")
    
    try:
        event_id = int(input("\nEnter Event ID to see feedback for: "))
        
        query = """
            SELECT s.name, s.srn, f.rating, f.comments
            FROM tbl_event_feedback f
            JOIN tbl_students s ON f.user_id = s.id
            WHERE f.event_id = %s
        """
        cursor.execute(query, (event_id,))
        feedback = cursor.fetchall()
        
        if not feedback:
            print("No feedback found for this event.")
            return
            
        print(f"\n--- Feedback Report for Event ID {event_id} ---")
        for row in feedback:
            # row[0]=student name, row[1]=srn, row[2]=rating, row[3]=comments
            print(f"Student: {row[0]} ({row[1]})")
            print(f"Rating:  {'⭐' * row[2]} ({row[2]}/5)")
            print(f"Comment: {row[3]}")
            print("-" * 20)
            
    except mysql.connector.Error as err:
        print(f"Error fetching feedback: {err}")
    except ValueError:
        print("Invalid input. Event ID must be a number.")

def main():
    """Main function to run the menu loop."""
    try:
        # Connect to DB
        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="root",  # <-- IMPORTANT: Change to your MySQL password
            database="pesu_project" # The DB you created
        )
        cursor = conn.cursor()
        print("\n✅ Successfully connected to 'event_management_db'")

    except mysql.connector.Error as err:
        if err.errno == errorcode.ER_BAD_DB_ERROR:
            print("Error: Database 'event_management_db' does not exist.")
            print("Please create the database and run the SQL script first.")
        elif err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            print("Error: Invalid MySQL username or password.")
        else:
            print(f"Error connecting to database: {err}")
        return # Exit if connection fails

    # --- Main Menu Loop ---
    while True:
        print("\n====== University Event Management System ======")
        print("1. List Available Venues")
        print("2. List Scheduled Events")
        print("3. Add New Student")
        print("4. Register Student for an Event")
        print("5. View Event Feedback")
        print("0. Exit")

        choice = input("Enter your choice: ")

        if choice == "1":
            list_available_venues(cursor)
        elif choice == "2":
            list_scheduled_events(cursor)
        elif choice == "3":
            add_new_student(cursor, conn)
        elif choice == "4":
            register_student_for_event(cursor, conn)
        elif choice == "5":
            show_event_feedback(cursor)
        elif choice == "0":
            print("Exiting Program...")
            break
        else:
            print("Invalid Choice. Try Again.")

    # Close Connection
    cursor.close()
    conn.close()
    print("Database connection closed.")

# Run the main program
if __name__ == "__main__":
    main()