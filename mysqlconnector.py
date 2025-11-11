import mysql.connector
from mysql.connector import errorcode
import datetime

# --- Helper Functions (No changes in these) ---

def list_available_venues(cursor):
    """Fetches and prints all venues marked as available."""
    print("\n--- 🏟️ Available Venues ---")
    try:
        cursor.execute("SELECT id, name, building, capacity FROM tbl_venues WHERE is_available = 1 ORDER BY capacity DESC")
        venues = cursor.fetchall()
        
        if not venues:
            print("No available venues found.")
            return None # Return None if no venues
            
        print(f"{'ID':<5} | {'Name':<25} | {'Building':<15} | {'Capacity':<10}")
        print("-" * 60)
        for row in venues:
            print(f"{row[0]:<5} | {row[1]:<25} | {row[2]:<15} | {row[3]:<10}")
        return venues # Return the list of venues
            
    except mysql.connector.Error as err:
        print(f"Error listing venues: {err}")
        return None

def list_all_venues(cursor):
    """Fetches and prints ALL venues with their availability status."""
    print("\n--- 🏟️ All Venues (with status) ---")
    try:
        cursor.execute("SELECT id, name, building, capacity, is_available FROM tbl_venues ORDER BY name")
        venues = cursor.fetchall()
        
        if not venues:
            print("No venues found in the database.")
            return
            
        print(f"{'ID':<5} | {'Name':<25} | {'Building':<15} | {'Capacity':<10} | {'Status':<15}")
        print("-" * 75)
        for row in venues:
            status_text = "Available" if row[4] == 1 else "Not Available"
            print(f"{row[0]:<5} | {row[1]:<25} | {row[2]:<15} | {row[3]:<10} | {status_text:<15}")
            
    except mysql.connector.Error as err:
        print(f"Error listing all venues: {err}")


def list_scheduled_events(cursor):
    """
    Fetches and prints all events where the end time is in the future.
    Returns True if events exist, False otherwise.
    """
    print("\n--- 🗓️ Upcoming & Ongoing Events ---")
    
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
        WHERE CONCAT(e.date, ' ', e.end_time) > NOW()
        ORDER BY e.date, e.start_time
    """
    try:
        cursor.execute(query)
        events = cursor.fetchall()
        
        if not events:
            print("No upcoming or ongoing events found.")
            return False 
            
        print(f"{'ID':<5} | {'Event Name':<25} | {'Date':<12} | {'Start':<10} | {'Venue':<20} | {'Host':<20}")
        print("-" * 95)
        for row in events:
            print(f"{row[0]:<5} | {row[1]:<25} | {str(row[2]):<12} | {str(row[3]):<10} | {row[4] or 'N/A':<20} | {row[5]:<20}")
        return True
        
    except mysql.connector.Error as err:
        print(f"Error listing events: {err}")
        return False

def list_completed_events(cursor):
    """
    Fetches and prints all events where the end time is in the past.
    Returns True if events exist, False otherwise.
    """
    print("\n--- 🏁 Completed Events ---")
    
    query = """
        SELECT 
            e.id, 
            e.name, 
            e.date, 
            e.end_time, 
            v.name AS venue_name, 
            h.name AS host_name
        FROM tbl_events e
        LEFT JOIN tbl_venues v ON e.location_id = v.id
        JOIN tbl_hosts h ON e.organizer_id = h.id
        WHERE CONCAT(e.date, ' ', e.end_time) <= NOW()
        ORDER BY e.date DESC, e.end_time DESC
    """
    try:
        cursor.execute(query)
        events = cursor.fetchall()
        
        if not events:
            print("No completed events found.")
            return False
            
        print(f"{'ID':<5} | {'Event Name':<25} | {'Date':<12} | {'End Time':<10} | {'Venue':<20} | {'Host':<20}")
        print("-" * 95)
        for row in events:
            print(f"{row[0]:<5} | {row[1]:<25} | {str(row[2]):<12} | {str(row[3]):<10} | {row[4] or 'N/A':<20} | {row[5]:<20}")
        return True
        
    except mysql.connector.Error as err:
        print(f"Error listing completed events: {err}")
        return False

def list_all_students(cursor):
    """
    Fetches and prints all students from tbl_students.
    Returns True if students exist, False otherwise.
    """
    print("\n--- 🧑‍🎓 All Students ---")
    try:
        cursor.execute("SELECT id, srn, name, semester, section FROM tbl_students ORDER BY name")
        students = cursor.fetchall()
        
        if not students:
            print("No students found in the database.")
            return False
            
        print(f"{'ID':<5} | {'SRN':<17} | {'Name':<25} | {'Sem':<5} | {'Sec':<5}")
        print("-" * 65)
        for row in students:
            print(f"{row[0]:<5} | {row[1]:<17} | {row[2]:<25} | {row[3]:<5} | {row[4]:<5}")
        return True
            
    except mysql.connector.Error as err:
        print(f"Error listing students: {err}")
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
        conn.commit()
        print(f"✅ Successfully added student: {name} ({srn})")
        
    except mysql.connector.Error as err:
        conn.rollback()
        if err.errno == 1062:
            print(f"Error: A student with SRN '{srn}' already exists.")
        else:
            print(f"Failed to add student: {err}")
    except ValueError:
        print("Invalid input. Semester must be a number.")

def order_ticket_and_register(cursor, conn):
    """
    Handles ordering one or more tickets, processing payment,
    updating ticket quantity, and registering the BUYER as a participant.
    """
    print("\n--- 🎟️ Order Ticket & Register for Event ---")
    
    try:
        # 1. Show available events
        if not list_scheduled_events(cursor):
            print("Cannot register for events as none are available.")
            return

        event_id = int(input("\nEnter the Event ID to register for: "))

        # 2. Find available tickets
        query_tickets = "SELECT id, ticket_type, price, quantity FROM tbl_tickets WHERE event_id = %s AND quantity > 0"
        cursor.execute(query_tickets, (event_id,))
        tickets = cursor.fetchall()

        if not tickets:
            print("Sorry, no tickets are available for this event or it's sold out.")
            return

        print("\n--- Available Tickets for this Event ---")
        print(f"{'ID':<5} | {'Type':<25} | {'Price':<10} | {'Available':<10}")
        print("-" * 55)
        for t in tickets:
            print(f"{t[0]:<5} | {t[1]:<25} | ${t[2]:<9} | {t[3]:<10}")
        
        ticket_id = int(input("\nEnter the Ticket ID you want to order: "))

        # 3. Validate ticket
        selected_ticket = None
        for t in tickets:
            if t[0] == ticket_id:
                selected_ticket = t
                break
        
        if selected_ticket is None:
            print("Error: Invalid Ticket ID for this event.")
            return
            
        ticket_price = selected_ticket[2]
        available_quantity = selected_ticket[3]

        # 4. Ask for number of tickets
        print(f"\nThere are {available_quantity} tickets of this type available.")
        how_many = int(input("How many tickets do you want to order? "))

        if how_many <= 0:
            print("You must order at least 1 ticket.")
            return
        if how_many > available_quantity:
            print(f"Error: You cannot order {how_many} tickets. Only {available_quantity} are available.")
            return

        # 5. Select student
        print("\n--- Select Student (Buyer) ---")
        if not list_all_students(cursor):
            print("No students found. Please add a student first.")
            return
        
        user_id = int(input("\nEnter the Student ID of the *buyer*: "))
        
        # 6. Handle Payment
        total_price = ticket_price * how_many
        print("\n--- Payment ---")
        print(f"Ticket: {selected_ticket[1]} (x{how_many})")
        print(f"Total Price: ${total_price:.2f}")
        
        payment_status = 'Pending'
        if total_price > 0:
            choice = input("Is payment completed? (y/n): ").strip().lower()
            if choice == 'y':
                payment_status = 'Completed'
            else:
                payment_status = 'Pending'
        else:
            print("This is a free ticket. Registration will be completed automatically.")
            payment_status = 'Completed'

        # 7. Database Transaction
        try:
            # 7a: Update (decrement) the quantity in tbl_tickets
            sql_update_tickets = "UPDATE tbl_tickets SET quantity = quantity - %s WHERE id = %s"
            cursor.execute(sql_update_tickets, (how_many, ticket_id))
            print(f"Reserving {how_many} tickets...")

            # 7b: Insert one row per ticket into tbl_orders
            sql_order = "INSERT INTO tbl_orders (ticket_id, user_id, order_time, payment_status) VALUES (%s, %s, %s, %s)"
            order_time = datetime.datetime.now()
            for _ in range(how_many):
                val_order = (ticket_id, user_id, order_time, payment_status)
                cursor.execute(sql_order, val_order)
            print(f"Created {how_many} order records with status: {payment_status}.")

            # 7c: If paid, register the BUYER in tbl_event_participants
            if payment_status == 'Completed':
                sql_register = "INSERT INTO tbl_event_participants (event_id, user_id, registration_time) VALUES (%s, %s, %s)"
                val_register = (event_id, user_id, order_time)
                cursor.execute(sql_register, val_register)
                print(f"✅ Successfully registered Student {user_id} (the buyer) for event {event_id}.")
            else:
                print(f"⚠️ Registration is pending. Please complete payment to attend.")
            
            conn.commit()
            print(f"\nTransaction complete. {how_many} tickets successfully booked by Student {user_id}.")

        except mysql.connector.Error as err:
            conn.rollback()
            print("\n❌ TRANSACTION FAILED. All changes have been rolled back.")
            if err.errno == 1062: 
                print("Error: This student is ALREADY registered for this event.")
            elif err.errno == 1452: 
                 print("Error: Invalid Student ID or Ticket ID. Please check and try again.")
            else:
                print(f"An unexpected error occurred: {err}")
        
    except ValueError:
        print("Invalid input. IDs and quantity must be numbers.")


def view_event_feedback(cursor):
    """Generates a report of feedback for a specific event."""
    print("\n--- 📊 View Event Feedback ---")
    
    cursor.execute("SELECT id, name FROM tbl_events ORDER BY date DESC")
    print("--- All Events (for feedback lookup) ---")
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
            print(f"Student: {row[0]} ({row[1]})")
            print(f"Rating:  {'⭐' * row[2]} ({row[2]}/5)")
            print(f"Comment: {row[3]}")
            print("-" * 20)
            
    except mysql.connector.Error as err:
        print(f"Error fetching feedback: {err}")
    except ValueError:
        print("Invalid input. Event ID must be a number.")

def write_event_feedback(cursor, conn):
    """
    Allows a student to write feedback for a completed event
    ONLY IF they were registered and their attendance was marked.
    """
    print("\n--- ✍️ Write Event Feedback ---")
    
    try:
        # 1. Select student
        print("\n--- Select Student ---")
        if not list_all_students(cursor):
            print("No students found.")
            return
        user_id = int(input("\nEnter your Student ID to leave feedback: "))
        
        # 2. Select a COMPLETED event
        print("\n--- Select a Completed Event ---")
        if not list_completed_events(cursor):
            print("No completed events are available to review.")
            return
        event_id = int(input("\nEnter the Event ID you want to review: "))
        
        # 3. Check participation AND attendance
        query_check_part = "SELECT attendance_status FROM tbl_event_participants WHERE event_id = %s AND user_id = %s"
        cursor.execute(query_check_part, (event_id, user_id))
        participant_record = cursor.fetchone()
        
        if participant_record is None:
            print("Error: You cannot leave feedback because you were not a registered participant for this event.")
            return
        
        if participant_record[0] == 0:
            print("Error: You cannot leave feedback because your attendance was not marked for this event.")
            return
            
        # 4. Check if student has ALREADY left feedback
        query_check_feedback = "SELECT id FROM tbl_event_feedback WHERE event_id = %s AND user_id = %s"
        cursor.execute(query_check_feedback, (event_id, user_id))
        feedback_record = cursor.fetchone()
        
        if feedback_record is not None:
            print("Error: You have already submitted feedback for this event.")
            return
            
        # 5. Get feedback
        print("\n--- You are eligible to leave feedback! (Attended) ---")
        rating = 0
        while True:
            try:
                rating = int(input("Enter rating (1-5): "))
                if 1 <= rating <= 5:
                    break
                else:
                    print("Invalid rating. Please enter a number between 1 and 5.")
            except ValueError:
                print("Invalid input. Please enter a number.")
                
        comments = input("Enter comments (optional): ")
        
        # 6. Insert feedback
        sql_insert = """
            INSERT INTO tbl_event_feedback (event_id, user_id, rating, comments, submitted_at) 
            VALUES (%s, %s, %s, %s, %s)
        """
        val_insert = (event_id, user_id, rating, comments, datetime.datetime.now())
        
        cursor.execute(sql_insert, val_insert)
        conn.commit()
        
        print("✅ Thank you! Your feedback has been submitted successfully.")

    except mysql.connector.Error as err:
        conn.rollback()
        print(f"An error occurred: {err}")
    except ValueError:
        print("Invalid input. IDs must be numbers.")


# --- Host & Admin Functions ---

def add_new_event(cursor, conn):
    """(Host) Adds a new event with venue capacity and time conflict checks."""
    print("\n--- 🗓️ Add New Event (Host Only) ---")
    try:
        # 1. Get basic details
        name = input("Enter event name: ")
        description = input("Enter event description: ")
        
        # 2. Get and validate date/times
        req_date_str = input("Enter event date (YYYY-MM-DD): ")
        req_start_str = input("Enter event start time (HH:MM:SS): ")
        req_end_str = input("Enter event end time (HH:MM:SS): ")
        
        req_start_dt = datetime.datetime.strptime(f"{req_date_str} {req_start_str}", '%Y-%m-%d %H:%M:%S')
        req_end_dt = datetime.datetime.strptime(f"{req_date_str} {req_end_str}", '%Y-%m-%d %H:%M:%S')

        if req_end_dt <= req_start_dt:
            print("Error: Event end time must be after the start time.")
            return
        
        # 3. Select Host
        if not list_all_hosts(cursor):
            print("Error: No hosts exist. Cannot create event.")
            return
        organizer_id = int(input("\nEnter the Host/Organizer ID: "))
        
        # 4. Select Venue
        venues = list_available_venues(cursor)
        if not venues:
            print("Error: No venues exist. Cannot create event.")
            return
        location_id = int(input("\nEnter the Venue ID: "))
        
        # 5. Venue Capacity Check (Dynamic max_participants)
        venue_capacity = None
        for v in venues:
            if v[0] == location_id:
                venue_capacity = v[3] # capacity is at index 3
                break
        if venue_capacity is None:
            print("Error: Invalid venue ID.")
            return
            
        print(f"--- Venue capacity is: {venue_capacity} ---")
        max_participants = int(input("Enter max participants for the event: "))
        
        if max_participants > venue_capacity:
            print(f"❌ Error: Max participants ({max_participants}) cannot exceed venue capacity ({venue_capacity}).")
            return
        
        # 6. Venue Time Conflict Check
        query_conflict = """
            SELECT id, name FROM tbl_events
            WHERE location_id = %s
            AND (CONCAT(date, ' ', start_time) < %s)
            AND (CONCAT(date, ' ', end_time) > %s)
        """
        cursor.execute(query_conflict, (location_id, req_end_dt, req_start_dt))
        conflicting_event = cursor.fetchone()
        
        if conflicting_event:
            print(f"\n❌ CONFLICT: This venue is already booked for '{conflicting_event[1]}' (Event ID: {conflicting_event[0]}) at this time.")
            return
        
        # 7. All checks passed - Insert the event
        print("\n✅ No conflicts found. Creating event...")
        sql_insert = """
            INSERT INTO tbl_events 
            (name, description, date, start_time, end_time, location_id, organizer_id, status, max_participants)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 'Scheduled', %s)
        """
        val_insert = (name, description, req_date_str, req_start_str, req_end_str, location_id, organizer_id, max_participants)
        
        cursor.execute(sql_insert, val_insert)
        conn.commit()
        print("✅ Success! New event has been scheduled.")
        
    except mysql.connector.Error as err:
        conn.rollback()
        print(f"An error occurred: {err}")
    except ValueError:
        print("Invalid input. Please enter a valid number or date/time format.")

# *** NEW FEATURE: Update Event ***
def update_event_details(cursor, conn):
    """(Host) Allows updating details, time, or location for an event."""
    print("\n--- ✏️ Update Event Details (Host Only) ---")
    if not list_scheduled_events(cursor):
        print("No upcoming events to update.")
        return
    try:
        event_id = int(input("\nEnter the Event ID to update: "))
        
        # Fetch current details
        cursor.execute("SELECT * FROM tbl_events WHERE id = %s", (event_id,))
        event = cursor.fetchone()
        if not event:
            print("Error: Event not found.")
            return

        print(f"Updating: {event[1]} (Event ID: {event[0]})")
        print("1. Update Name / Description")
        print("2. Update Date / Time")
        print("3. Update Location (Venue)")
        choice = input("What do you want to update? ")

        if choice == "1":
            new_name = input(f"Enter new name ({event[1]}): ") or event[1]
            new_desc = input("Enter new description: ") or event[2]
            
            sql_update = "UPDATE tbl_events SET name = %s, description = %s WHERE id = %s"
            cursor.execute(sql_update, (new_name, new_desc, event_id))
            conn.commit()
            print("✅ Event name/description updated.")

        elif choice == "2":
            # Must re-check time conflicts
            print("Enter new date and time.")
            req_date_str = input(f"Enter event date ({event[3]}): ") or event[3]
            req_start_str = input(f"Enter event start time ({event[4]}): ") or event[4]
            req_end_str = input(f"Enter event end time ({event[5]}): ") or event[5]
            
            req_start_dt = datetime.datetime.strptime(f"{req_date_str} {req_start_str}", '%Y-%m-%d %H:%M:%S')
            req_end_dt = datetime.datetime.strptime(f"{req_date_str} {req_end_str}", '%Y-%m-%d %H:%M:%S')

            if req_end_dt <= req_start_dt:
                print("Error: Event end time must be after the start time.")
                return

            # Check conflict with the *same location* (but NOT this event itself)
            query_conflict = """
                SELECT id, name FROM tbl_events
                WHERE location_id = %s
                AND id != %s
                AND (CONCAT(date, ' ', start_time) < %s)
                AND (CONCAT(date, ' ', end_time) > %s)
            """
            cursor.execute(query_conflict, (event[6], event_id, req_end_dt, req_start_dt))
            if cursor.fetchone():
                print("❌ CONFLICT: The new time overlaps with another event at this location.")
                return
            
            sql_update = "UPDATE tbl_events SET date = %s, start_time = %s, end_time = %s WHERE id = %s"
            cursor.execute(sql_update, (req_date_str, req_start_str, req_end_str, event_id))
            conn.commit()
            print("✅ Event time updated.")
            
        elif choice == "3":
            # Must re-check capacity and time conflicts at NEW location
            venues = list_available_venues(cursor)
            if not venues: return
            new_location_id = int(input(f"Enter new Venue ID ({event[6]}): "))
            
            # Get new capacity
            venue_capacity = None
            for v in venues:
                if v[0] == new_location_id:
                    venue_capacity = v[3]
                    break
            if venue_capacity is None:
                print("Error: Invalid new venue ID.")
                return
                
            if event[8] > venue_capacity:
                print(f"❌ Error: Event max participants ({event[8]}) exceeds new venue capacity ({venue_capacity}).")
                return

            # Check conflict at NEW location
            event_start_dt = datetime.datetime.combine(event[3], event[4])
            event_end_dt = datetime.datetime.combine(event[3], event[5])
            query_conflict = """
                SELECT id, name FROM tbl_events
                WHERE location_id = %s
                AND (CONCAT(date, ' ', start_time) < %s)
                AND (CONCAT(date, ' ', end_time) > %s)
            """
            cursor.execute(query_conflict, (new_location_id, event_end_dt, event_start_dt))
            if cursor.fetchone():
                print("❌ CONFLICT: The new venue is booked by another event at this time.")
                return
                
            sql_update = "UPDATE tbl_events SET location_id = %s WHERE id = %s"
            cursor.execute(sql_update, (new_location_id, event_id))
            conn.commit()
            print("✅ Event location updated.")
        
        else:
            print("Invalid choice.")

    except mysql.connector.Error as err:
        conn.rollback()
        print(f"An error occurred: {err}")
    except ValueError:
        print("Invalid input. IDs must be numbers.")


# *** NEW FEATURE: Manage Tickets ***
def manage_event_tickets(cursor, conn):
    """(Host) Add new ticket types or update quantities for an event."""
    print("\n--- manage_event_tickets (Host Only) ---")
    try:
        cursor.execute("SELECT id, name FROM tbl_events")
        for row in cursor.fetchall(): print(f"ID: {row[0]}, Name: {row[1]}")
        event_id = int(input("\nEnter the Event ID to manage tickets for: "))
        
        # Show existing tickets
        print("\n--- Existing Tickets for this Event ---")
        query_tickets = "SELECT id, ticket_type, price, quantity FROM tbl_tickets WHERE event_id = %s"
        cursor.execute(query_tickets, (event_id,))
        tickets = cursor.fetchall()
        for t in tickets: print(f"ID: {t[0]:<5} | {t[1]:<25} | ${t[2]:<9} | Qty: {t[3]:<10}")

        print("\n1. Add a new ticket type")
        print("2. Update an existing ticket")
        choice = input("Enter your choice: ")
        
        if choice == "1":
            ticket_type = input("Enter new ticket type name (e.g., Early Bird): ")
            price = float(input("Enter price: "))
            quantity = int(input("Enter total quantity available: "))
            
            sql_insert = "INSERT INTO tbl_tickets (event_id, ticket_type, price, quantity) VALUES (%s, %s, %s, %s)"
            cursor.execute(sql_insert, (event_id, ticket_type, price, quantity))
            conn.commit()
            print("✅ New ticket type added.")
        
        elif choice == "2":
            ticket_id = int(input("Enter the Ticket ID to update: "))
            new_price = float(input("Enter new price (press Enter to skip): ") or -1)
            new_qty = int(input("Enter new total quantity (press Enter to skip): ") or -1)

            # Build the query dynamically
            updates = []
            params = []
            if new_price >= 0:
                updates.append("price = %s")
                params.append(new_price)
            if new_qty >= 0:
                updates.append("quantity = %s")
                params.append(new_qty)
            
            if not updates:
                print("No changes specified.")
                return

            params.append(ticket_id)
            params.append(event_id)
            
            sql_update = f"UPDATE tbl_tickets SET {', '.join(updates)} WHERE id = %s AND event_id = %s"
            cursor.execute(sql_update, tuple(params))
            conn.commit()
            print("✅ Ticket updated.")

    except mysql.connector.Error as err:
        conn.rollback()
        print(f"An error occurred: {err}")
    except ValueError:
        print("Invalid input. IDs, prices, and quantities must be numbers.")


def toggle_venue_availability(cursor, conn):
    """(Host) Manually marks a venue as available or not available."""
    print("\n--- 🔄 Update Venue Availability (Host Only) ---")
    try:
        list_all_venues(cursor)
        venue_id = int(input("\nEnter Venue ID to update: "))
        print("Set status: 1 = Available, 0 = Not Available")
        new_status = int(input("Enter new status (0 or 1): "))
        
        if new_status not in [0, 1]:
            print("Error: Invalid status. Must be 0 or 1.")
            return
            
        sql_update = "UPDATE tbl_venues SET is_available = %s WHERE id = %s"
        cursor.execute(sql_update, (new_status, venue_id))
        
        if cursor.rowcount == 0:
            print("Error: No matching venue ID found.")
        else:
            conn.commit()
            print("✅ Venue availability updated successfully.")

    except mysql.connector.Error as err:
        conn.rollback()
        print(f"An error occurred: {err}")
    except ValueError:
        print("Invalid input. IDs must be numbers.")


def mark_attendance(cursor, conn):
    """(Host) Marks a registered student's attendance as 1."""
    print("\n--- 🧑‍💼 Mark Event Attendance (Host Only) ---")
    try:
        # 1. Select an event
        cursor.execute("SELECT id, name FROM tbl_events ORDER BY date DESC")
        events = cursor.fetchall()
        if not events:
            print("No events found.")
            return
            
        print("--- All Events ---")
        for row in events:
            print(f"ID: {row[0]}, Name: {row[1]}")
        event_id = int(input("\nEnter Event ID to mark attendance for: "))

        # 2. List registered students for that event
        query = """
            SELECT s.id, s.name, s.srn, p.attendance_status
            FROM tbl_event_participants p
            JOIN tbl_students s ON p.user_id = s.id
            WHERE p.event_id = %s
            ORDER BY s.name
        """
        cursor.execute(query, (event_id,))
        participants = cursor.fetchall()

        if not participants:
            print("No students are registered for this event.")
            return

        print(f"\n--- Registered Students for Event ID {event_id} ---")
        print(f"{'Student ID':<12} | {'Name':<25} | {'SRN':<17} | {'Attended?':<10}")
        print("-" * 68)
        for row in participants:
            attended_text = "Yes" if row[3] == 1 else "No"
            print(f"{row[0]:<12} | {row[1]:<25} | {row[2]:<17} | {attended_text:<10}")
        
        # 3. Get student to mark
        user_id = int(input("\nEnter Student ID to mark as 'Attended' (1): "))

        # 4. Update the database
        sql_update = "UPDATE tbl_event_participants SET attendance_status = 1 WHERE event_id = %s AND user_id = %s"
        cursor.execute(sql_update, (event_id, user_id))
        
        if cursor.rowcount == 0:
            print("Error: No matching student registration found for that event. No changes made.")
        else:
            conn.commit()
            print(f"✅ Successfully marked Student {user_id} as attended for Event {event_id}.")

    except mysql.connector.Error as err:
        conn.rollback()
        print(f"An error occurred: {err}")
    except ValueError:
        print("Invalid input. IDs must be numbers.")

def list_all_participants(cursor):
    """(Host) Shows a detailed list of all participants for all events."""
    print("\n--- 👥 All Event Participants (Detailed) ---")
    try:
        query = """
            SELECT e.name, s.name, s.srn, p.registration_time, p.attendance_status
            FROM tbl_event_participants p
            JOIN tbl_events e ON p.event_id = e.id
            JOIN tbl_students s ON p.user_id = s.id
            ORDER BY e.name, s.name
        """
        cursor.execute(query)
        records = cursor.fetchall()
        
        if not records:
            print("No participant records found.")
            return
            
        print(f"{'Event Name':<25} | {'Student Name':<25} | {'SRN':<17} | {'Attended?':<10}")
        print("-" * 81)
        for row in records:
            attended_text = "Yes" if row[4] == 1 else "No"
            print(f"{row[0]:<25} | {row[1]:<25} | {row[2]:<17} | {attended_text:<10}")

    except mysql.connector.Error as err:
        print(f"Error listing participants: {err}")

def list_participant_counts(cursor):
    """(Host) Shows a summary of participant counts for each event."""
    print("\n--- 📊 Participant Count by Event (Summary) ---")
    try:
        query = """
            SELECT e.name, COUNT(p.user_id) AS participant_count
            FROM tbl_event_participants p
            JOIN tbl_events e ON p.event_id = e.id
            GROUP BY p.event_id, e.name
            ORDER BY participant_count DESC
        """
        cursor.execute(query)
        records = cursor.fetchall()
        
        if not records:
            print("No participant records found.")
            return

        print(f"{'Event Name':<30} | {'Total Registered':<20}")
        print("-" * 55)
        for row in records:
            print(f"{row[0]:<30} | {row[1]:<20}")

    except mysql.connector.Error as err:
        print(f"Error listing participant counts: {err}")

def list_all_resources(cursor):
    """Fetches and prints all resources."""
    print("\n--- 📦 All Resources ---")
    try:
        cursor.execute("SELECT id, name, type, quantity, maintenance_status FROM tbl_resources ORDER BY name")
        resources = cursor.fetchall()
        
        if not resources:
            print("No resources found.")
            return None
        
        print(f"{'ID':<5} | {'Name':<25} | {'Type':<15} | {'Total Qty':<10} | {'Status':<15}")
        print("-" * 75)
        for row in resources:
            print(f"{row[0]:<5} | {row[1]:<25} | {row[2]:<15} | {row[3]:<10} | {row[4]:<15}")
        return resources
            
    except mysql.connector.Error as err:
        print(f"Error listing resources: {err}")
        return None

def add_new_resource(cursor, conn):
    """(Host) Adds a new resource to the tbl_resources."""
    print("\n--- 📦 Add New Resource (Host Only) ---")
    try:
        name = input("Enter resource name: ")
        type = input("Enter resource type (e.g., AV Equipment): ")
        quantity = int(input("Enter total quantity: "))
        description = input("Enter description: ")

        if quantity < 0:
            print("Error: Quantity cannot be negative.")
            return

        sql_insert = """
            INSERT INTO tbl_resources (name, type, quantity, description, is_available, maintenance_status)
            VALUES (%s, %s, %s, %s, 1, 'Available')
        """
        val_insert = (name, type, quantity, description)
        
        cursor.execute(sql_insert, val_insert)
        conn.commit()
        print(f"✅ Success! Resource '{name}' has been added.")

    except mysql.connector.Error as err:
        conn.rollback()
        print(f"An error occurred: {err}")
    except ValueError:
        print("Invalid input. Quantity must be a number.")

def toggle_resource_status(cursor, conn):
    """(Host) Manually updates a resource's status."""
    print("\n--- 🔄 Update Resource Status (Host Only) ---")
    try:
        if not list_all_resources(cursor):
            return
        
        resource_id = int(input("\nEnter Resource ID to update: "))
        print("Example statuses: 'Available', 'Under Maintenance', 'Damaged'")
        new_status = input("Enter new maintenance status: ")
        
        # is_available is 1 only if the new status is 'Available'
        is_available = 1 if new_status.lower() == 'available' else 0
        
        sql_update = "UPDATE tbl_resources SET maintenance_status = %s, is_available = %s WHERE id = %s"
        cursor.execute(sql_update, (new_status, is_available, resource_id))
        
        if cursor.rowcount == 0:
            print("Error: No matching resource ID found.")
        else:
            conn.commit()
            print("✅ Resource status updated successfully.")

    except mysql.connector.Error as err:
        conn.rollback()
        print(f"An error occurred: {err}")
    except ValueError:
        print("Invalid input. IDs must be numbers.")

def add_resource_maintenance(cursor, conn):
    """(Host) Schedules resource maintenance, checking for booking conflicts."""
    print("\n--- 🛠️ Schedule Resource Maintenance (Host Only) ---")
    try:
        if not list_all_resources(cursor):
            return
        resource_id = int(input("\nEnter Resource ID to schedule maintenance for: "))
        
        print("\nEnter maintenance start and end times in 'YYYY-MM-DD HH:MM:SS' format.")
        start_str = input("Enter maintenance start: ")
        end_str = input("Enter maintenance end: ")
        description = input("Enter maintenance description: ")
        
        req_start = datetime.datetime.strptime(start_str, '%Y-%m-%d %H:%M:%S')
        req_end = datetime.datetime.strptime(end_str, '%Y-%m-%d %H:%M:%S')

        if req_end <= req_start:
            print("Error: Maintenance end time must be after the start time.")
            return
            
        # Conflict Check: See if this resource is already booked for an event
        query_conflict = """
            SELECT e.name
            FROM tbl_event_resources er
            JOIN tbl_events e ON er.event_id = e.id
            WHERE er.resource_id = %s
            AND (er.booking_start < %s) AND (er.booking_end > %s)
        """
        cursor.execute(query_conflict, (resource_id, req_end, req_start))
        conflicting_booking = cursor.fetchone()
        
        if conflicting_booking:
            print(f"\n❌ CONFLICT: Cannot schedule. This resource is booked for '{conflicting_booking[0]}' during this time.")
            return

        # All clear, schedule maintenance
        print("\n✅ No conflicts found. Scheduling maintenance...")
        sql_insert = """
            INSERT INTO tbl_resource_maintenance (resource_id, maintenance_start, maintenance_end, description)
            VALUES (%s, %s, %s, %s)
        """
        val_insert = (resource_id, req_start, req_end, description)
        
        cursor.execute(sql_insert, val_insert)
        
        # Also update the resource status
        sql_update = "UPDATE tbl_resources SET is_available = 0, maintenance_status = 'Under Maintenance' WHERE id = %s"
        cursor.execute(sql_update, (resource_id,))
        
        conn.commit()
        print("✅ Success! Resource maintenance scheduled and status updated.")

    except mysql.connector.Error as err:
        conn.rollback()
        print(f"An error occurred: {err}")
    except ValueError:
        print("Invalid input. Please enter a valid date/time format.")
        

def book_event_resource(cursor, conn):
    """(Host) Books a resource for an event, checking for conflicts."""
    print("\n--- 📦 Book a Resource for an Event (Host Only) ---")
    try:
        # 1. Select an event
        if not list_scheduled_events(cursor):
            print("No upcoming events to book for.")
            return
        event_id = int(input("\nEnter the Event ID to book resources for: "))

        # 2. Select a resource
        resources = list_all_resources(cursor)
        if not resources:
            return
        resource_id = int(input("\nEnter the Resource ID to book: "))
        
        total_available_quantity = None
        for r in resources:
            if r[0] == resource_id:
                total_available_quantity = r[3]
                break
        if total_available_quantity is None:
            print("Error: Invalid resource ID.")
            return

        # 3. Get Quantity
        quantity_to_book = int(input(f"How many '{r[1]}' to book (Total available: {total_available_quantity})? "))
        
        if quantity_to_book > total_available_quantity:
            print(f"Error: You cannot book {quantity_to_book}. Only {total_available_quantity} exist in total.")
            return
        if quantity_to_book <= 0:
            print("Error: You must book at least 1.")
            return

        # 4. Get Booking Times
        print("\nEnter booking start and end times in 'YYYY-MM-DD HH:MM:SS' format.")
        book_start_str = input("Enter booking start: ")
        book_end_str = input("Enter booking end: ")
        
        req_start = datetime.datetime.strptime(book_start_str, '%Y-%m-%d %H:%M:%S')
        req_end = datetime.datetime.strptime(book_end_str, '%Y-%m-%d %H:%M:%S')

        if req_end <= req_start:
            print("Error: Booking end time must be after the start time.")
            return

        # 5. Start Transaction and Run Conflict Checks
        try:
            # Check 2: Maintenance Conflict
            query_maint = """
                SELECT 1 FROM tbl_resource_maintenance
                WHERE resource_id = %s
                AND (maintenance_start < %s) AND (maintenance_end > %s)
            """
            cursor.execute(query_maint, (resource_id, req_end, req_start))
            if cursor.fetchone():
                print("\n❌ CONFLICT: This resource is scheduled for maintenance during this time.")
                return

            # Check 3: Booking Conflict (Quantity Overlap)
            query_booked = """
                SELECT SUM(quantity_booked)
                FROM tbl_event_resources
                WHERE resource_id = %s
                AND (booking_start < %s) AND (booking_end > %s)
            """
            cursor.execute(query_booked, (resource_id, req_end, req_start))
            total_booked_during_slot = cursor.fetchone()[0] or 0
            
            remaining_qty = total_available_quantity - total_booked_during_slot
            
            if quantity_to_book > remaining_qty:
                print(f"\n❌ CONFLICT: {total_booked_during_slot} units are already booked during this slot.")
                print(f"You can only book up to {remaining_qty} more units.")
                return

            # 6. All Checks Passed - Execute Booking
            print(f"\n✅ No conflicts found. {remaining_qty} units are available. Booking {quantity_to_book}...")
            sql_insert = """
                INSERT INTO tbl_event_resources 
                (event_id, resource_id, quantity_booked, booking_start, booking_end) 
                VALUES (%s, %s, %s, %s, %s)
            """
            val_insert = (event_id, resource_id, quantity_to_book, req_start, req_end)
            
            cursor.execute(sql_insert, val_insert)
            conn.commit()
            print("✅ Success! Resource has been booked for the event.")

        except mysql.connector.Error as err:
            conn.rollback()
            print(f"\n❌ DATABASE ERROR. Transaction rolled back. {err}")
        
    except ValueError:
        print("Invalid input. Please enter a valid number or date/time format.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

def list_all_hosts(cursor):
    """Fetches and prints all hosts."""
    print("\n--- 🧑‍💼 All Hosts ---")
    try:
        cursor.execute("SELECT id, name, department, role FROM tbl_hosts ORDER BY name")
        hosts = cursor.fetchall()
        
        if not hosts:
            print("No hosts found.")
            return None
        
        print(f"{'ID':<5} | {'Name':<25} | {'Department':<25} | {'Role':<20}")
        print("-" * 80)
        for row in hosts:
            print(f"{row[0]:<5} | {row[1]:<25} | {row[2]:<25} | {row[3]:<20}")
        return hosts
            
    except mysql.connector.Error as err:
        print(f"Error listing hosts: {err}")
        return None

def add_new_host(cursor, conn):
    """(Host) Adds a new host to the tbl_hosts."""
    print("\n--- 🧑‍💼 Add New Host (Host Only) ---")
    try:
        name = input("Enter host name: ")
        email = input("Enter host email: ")
        phone = input("Enter host phone (optional): ")
        role = input("Enter host role (e.g., Professor): ")
        department = input("Enter host department (optional): ")
        
        phone = phone if phone else None
        department = department if department else None

        sql_insert = """
            INSERT INTO tbl_hosts (name, email, phone, role, department)
            VALUES (%s, %s, %s, %s, %s)
        """
        val_insert = (name, email, phone, role, department)
        
        cursor.execute(sql_insert, val_insert)
        conn.commit()
        print(f"✅ Success! Host '{name}' has been added.")

    except mysql.connector.Error as err:
        conn.rollback()
        if err.errno == 1062: # Duplicate entry
            print(f"Error: A host with that email or phone already exists.")
        else:
            print(f"An error occurred: {err}")
    except ValueError:
        print("Invalid input.")

def show_server_time(cursor):
    """Prints the current timestamp from the MySQL server."""
    print("\n--- 🕒 Checking Server Time ---")
    try:
        cursor.execute("SELECT NOW()")
        server_time = cursor.fetchone()[0]
        print(f"Your MySQL server's current time is: {server_time}")
    except mysql.connector.Error as err:
        print(f"Error checking server time: {err}")

# --- Student Portal Functions ---

# *** NEW FEATURE: My Registrations ***
def my_registrations(cursor, user_id):
    """(Student) Shows upcoming events the student is registered for."""
    print("\n--- 🎫 My Upcoming Registrations ---")
    query = """
        SELECT e.id, e.name, e.date, e.start_time, v.name
        FROM tbl_event_participants p
        JOIN tbl_events e ON p.event_id = e.id
        LEFT JOIN tbl_venues v ON e.location_id = v.id
        WHERE p.user_id = %s
        AND CONCAT(e.date, ' ', e.end_time) > NOW()
        ORDER BY e.date
    """
    cursor.execute(query, (user_id,))
    registrations = cursor.fetchall()
    
    if not registrations:
        print("You are not registered for any upcoming events.")
        return False

    print(f"{'Event ID':<10} | {'Event Name':<25} | {'Date':<12} | {'Venue':<25}")
    print("-" * 75)
    for row in registrations:
        print(f"{row[0]:<10} | {row[1]:<25} | {str(row[2]):<12} | {row[4] or 'N/A':<25}")
    return True
        
# *** NEW FEATURE: Cancel Registration ***
def cancel_registration(cursor, conn, user_id):
    """(Student) Cancels a registration for an event."""
    print("\n--- 🚫 Cancel Registration ---")
    
    # Show them what they can cancel
    if not my_registrations(cursor, user_id):
        return
        
    try:
        event_id = int(input("\nEnter the Event ID to cancel your registration for: "))
        
        # We must perform this as a transaction
        try:
            # 1. Delete them from the participants list
            sql_delete_part = "DELETE FROM tbl_event_participants WHERE event_id = %s AND user_id = %s"
            cursor.execute(sql_delete_part, (event_id, user_id))
            
            if cursor.rowcount == 0:
                print("Error: You are not registered for that event.")
                conn.rollback()
                return

            # 2. Delete their order(s) for that event
            # This finds the ticket IDs for the event and deletes orders matching
            sql_delete_order = """
                DELETE FROM tbl_orders 
                WHERE user_id = %s 
                AND ticket_id IN (SELECT id FROM tbl_tickets WHERE event_id = %s)
            """
            cursor.execute(sql_delete_order, (user_id, event_id))
            
            # 3. Add quantity back to tickets. This is tricky.
            # We'll add +1 to the *first* ticket type for that event as a simple refund.
            # A real system would need a link between tbl_orders and tbl_event_participants.
            sql_refund_ticket = """
                UPDATE tbl_tickets 
                SET quantity = quantity + 1 
                WHERE event_id = %s 
                ORDER BY id 
                LIMIT 1
            """
            cursor.execute(sql_refund_ticket, (event_id,))
            
            conn.commit()
            print("✅ Your registration has been cancelled. One ticket has been refunded to the pool.")
            
        except mysql.connector.Error as err:
            conn.rollback()
            print(f"Error during cancellation: {err}")
            
    except ValueError:
        print("Invalid Event ID.")


# --- Main Application Logic ---

def student_portal(cursor, conn):
    """Shows the menu for a logged-in student."""
    print("\n--- 🧑‍🎓 Student Portal ---")
    if not list_all_students(cursor):
        print("No students found in system.")
        return
    try:
        user_id = int(input("Enter your Student ID to log in: "))
        # Validate student ID
        cursor.execute("SELECT name FROM tbl_students WHERE id = %s", (user_id,))
        student = cursor.fetchone()
        if not student:
            print("Error: Student ID not found.")
            return
        
        print(f"Welcome, {student[0]}!")
        
        while True:
            print("\n--- Student Menu ---")
            print("1. My Upcoming Registrations")
            print("2. Cancel a Registration")
            print("3. Register for a New Event")
            print("4. List All Upcoming Events")
            print("5. List All Completed Events")
            print("6. Write Event Feedback")
            print("0. Log Out (Return to Main Menu)")
            
            choice = input("Enter your choice: ")
            
            if choice == "1":
                my_registrations(cursor, user_id)
            elif choice == "2":
                cancel_registration(cursor, conn, user_id)
            elif choice == "3":
                order_ticket_and_register(cursor, conn)
            elif choice == "4":
                list_scheduled_events(cursor)
            elif choice == "5":
                list_completed_events(cursor)
            elif choice == "6":
                write_event_feedback(cursor, conn)
            elif choice == "0":
                print("Logging out...")
                break
            else:
                print("Invalid choice.")
                
    except ValueError:
        print("Invalid ID. Please enter a number.")
    
def admin_portal(cursor, conn):
    """Shows the menu for a host or admin."""
    while True:
        print("\n========== 🧑‍💼 Host & Admin Portal ==========")
        print("--- Event Management ---")
        print(" 1. Add New Event")
        print(" 2. Update Event Details")
        print(" 3. Manage Event Tickets")
        print(" 4. Mark Event Attendance")
        print(" 5. View All Participants (Detail)")
        print(" 6. View Participant Counts (Summary)")
        
        print("\n--- Asset Management ---")
        print(" 7. List ALL Venues (with status)")
        print(" 8. Update Venue Availability")
        print(" 9. Book Resource for Event")
        print("10. Add New Resource")
        print("11. Update Resource Status")
        print("12. Schedule Resource Maintenance")
        
        print("\n--- User Management ---")
        print("13. Add New Host")
        print("14. View All Hosts")
        print("15. List All Students")
        print("16. Add New Student")
        
        print("\n--- System ---")
        print("17. Check Server Time")
        print(" 0. Log Out (Return to Main Menu)")

        choice = input("Enter your choice: ")

        if choice == "1":
            add_new_event(cursor, conn)
        elif choice == "2":
            update_event_details(cursor, conn)
        elif choice == "3":
            manage_event_tickets(cursor, conn)
        elif choice == "4":
            mark_attendance(cursor, conn)
        elif choice == "5":
            list_all_participants(cursor)
        elif choice == "6":
            list_participant_counts(cursor)
        elif choice == "7":
            list_all_venues(cursor)
        elif choice == "8":
            toggle_venue_availability(cursor, conn)
        elif choice == "9":
            book_event_resource(cursor, conn)
        elif choice == "10":
            add_new_resource(cursor, conn)
        elif choice == "11":
            toggle_resource_status(cursor, conn)
        elif choice == "12":
            add_resource_maintenance(cursor, conn)
        elif choice == "13":
            add_new_host(cursor, conn)
        elif choice == "14":
            list_all_hosts(cursor)
        elif choice == "15":
            list_all_students(cursor)
        elif choice == "16":
            add_new_student(cursor, conn)
        elif choice == "17":
            show_server_time(cursor)
        elif choice == "0":
            print("Logging out...")
            break
        else:
            print("Invalid Choice. Try Again.")

def main():
    """Main function to run the application."""
    try:
        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="root",  # <-- IMPORTANT: Change to your MySQL password
            database="pesu_project" # Make sure this matches your database name
        )
        cursor = conn.cursor()
        print("\n✅ Successfully connected to 'pesu_project'")

    except mysql.connector.Error as err:
        if err.errno == errorcode.ER_BAD_DB_ERROR:
            print(f"Error: Database '{'pesu_project'}' does not exist.")
        elif err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            print("Error: Invalid MySQL username or password.")
        else:
            print(f"Error connecting to database: {err}")
        return

    # --- Main Application Loop ---
    while True:
        print("\n====== University Event Management System ======")
        print("1. Student Portal")
        print("2. Host / Admin Portal")
        print("3. View Public Event Feedback")
        print("0. Exit")
        
        choice = input("Enter your choice: ")
        
        if choice == "1":
            student_portal(cursor, conn)
        elif choice == "2":
            admin_portal(cursor, conn)
        elif choice == "3":
            view_event_feedback(cursor) # Public can view feedback1
        elif choice == "0":
            print("Exiting Program...")
            break
        else:
            print("Invalid Choice. Try Again.")

    # Close Connection
    cursor.close()
    conn.close()
    print("Database connection closed.")

if __name__ == "__main__":
    main()