import streamlit as st
import mysql.connector
from mysql.connector import errorcode
import datetime
import pandas as pd 

# --- CONFIGURATION & CACHING ---
st.set_page_config(layout="wide", page_title="PESU Event Management System")

# IMPORTANT: Replace with your actual MySQL credentials
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "root",  # <-- IMPORTANT: Change this
    "database": "pesu_project"
}

@st.cache_resource(ttl=3600)
def init_connection():
    """Initializes and caches the database connection."""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        if not conn.is_connected():
            raise Exception("Connection failed after initialization.")
        return conn
    except mysql.connector.Error as err:
        st.error(f"Error connecting to database: {err.msg}")
        st.stop()
    except Exception as e:
        st.error(f"An unexpected error occurred during database connection: {e}")
        st.stop()

conn = init_connection()

# --- STREAMLIT SESSION STATE MANAGEMENT ---
if 'logged_in_user_id' not in st.session_state:
    st.session_state['logged_in_user_id'] = None
if 'page' not in st.session_state:
    st.session_state['page'] = 'main' 

# --- GENERAL HELPER FUNCTIONS ---

def convert_to_time(td):
    """
    Converts datetime.timedelta (returned by MySQL for TIME column) 
    to datetime.time, which st.time_input requires.
    """
    if isinstance(td, datetime.timedelta):
        total_seconds = int(td.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        return datetime.time(hours, minutes, seconds)
    elif isinstance(td, datetime.time):
        return td
    elif isinstance(td, str):
        try:
            h, m, s = map(int, td.split(':'))
            return datetime.time(h, m, s)
        except:
            pass
    return datetime.time(0, 0, 0)

def execute_query(query, params=None, fetch_type='all'):
    """Utility to safely execute SELECT queries and return data."""
    try:
        cursor = conn.cursor(buffered=True)
        cursor.execute(query, params)
        
        if fetch_type == 'one':
            result = cursor.fetchone()
        elif fetch_type == 'all':
            result = cursor.fetchall()
        else:
            result = True 
            
        cursor.close()
        return result
    except mysql.connector.Error as err:
        st.error(f"Database Read Error: {err.msg}")
        return None

def commit_transaction(sql, val):
    """Utility to perform INSERT/UPDATE/DELETE with commit/rollback."""
    try:
        cursor = conn.cursor(buffered=True)
        cursor.execute(sql, val)
        conn.commit()
        cursor.close()
        return True
    except mysql.connector.Error as err:
        conn.rollback()
        cursor.close()
        if err.errno == errorcode.ER_DUP_ENTRY:
            return "Duplicate entry error."
        elif err.errno == errorcode.ER_NO_REFERENCED_ROW_2:
            return "Foreign key constraint failed (Invalid ID)."
        else:
            return f"Database Write Error: {err.msg}"
    except Exception as e:
        conn.rollback()
        return f"Unexpected Error: {e}"

# --- DATA FETCH HELPERS ---

def list_all_students(cursor=None):
    """Fetches all students."""
    if cursor is None:
        students = execute_query("SELECT id, srn, name, semester, section FROM tbl_students ORDER BY name")
        return students
    return execute_query("SELECT id, srn, name, semester, section FROM tbl_students ORDER BY name", cursor=cursor)

def list_all_hosts():
    """Fetches all hosts."""
    return execute_query("SELECT id, name, department, role FROM tbl_hosts ORDER BY name")

def list_all_venues():
    """Fetches all venues."""
    return execute_query("SELECT id, name, building, capacity, is_available FROM tbl_venues ORDER BY name")

def list_available_venues():
    """Fetches only available venues."""
    return execute_query("SELECT id, name, building, capacity FROM tbl_venues WHERE is_available = 1 ORDER BY capacity DESC")

def list_scheduled_events():
    """Fetches upcoming events for display."""
    query = """
        SELECT
            e.id,
            e.name,
            e.description,
            e.date,
            e.start_time,
            e.end_time,
            v.name AS venue_name,
            h.name AS host_name,
            e.location_id
        FROM tbl_events e
        LEFT JOIN tbl_venues v ON e.location_id = v.id
        JOIN tbl_hosts h ON e.organizer_id = h.id
        WHERE CONCAT(e.date, ' ', e.end_time) > NOW()
        ORDER BY e.date, e.start_time
    """
    return execute_query(query)

def list_all_resources():
    """Fetches all resources."""
    return execute_query("SELECT id, name, type, quantity, maintenance_status FROM tbl_resources ORDER BY name")

# --- PORTAL FUNCTIONS (Streamlit Interface) ---

def main_menu():
    """The main entry point for the Streamlit app."""
    st.title("🏛️ University Event Management System")
    st.markdown("Welcome to the PESU Event Management System. Please select a portal to proceed.")
    
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("🧑‍🎓 Student Portal", use_container_width=True):
            st.session_state['page'] = 'student_login'
            st.rerun()

    with col2:
        if st.button("🧑‍💼 Host / Admin Portal", use_container_width=True):
            st.session_state['page'] = 'admin_portal'
            st.rerun()

    with col3:
        if st.button("📊 View Public Feedback", use_container_width=True):
            st.session_state['page'] = 'view_feedback_public'
            st.rerun()
            
    st.divider()

def student_login_page():
    """Handles student login and redirection."""
    st.header("🧑‍🎓 Student Login")
    students = list_all_students()

    if students:
        student_map = {s[0]: f"{s[2]} ({s[1]})" for s in students}
        
        valid_options = list(student_map.keys())
        if not valid_options:
            st.warning("No valid student IDs found.")
            return

        selected_id = st.selectbox(
            "Select your Student ID:",
            options=valid_options,
            format_func=lambda x: student_map.get(x, 'Select Student')
        )
        
        if st.button("Log In", key="student_login_btn"):
            st.session_state['logged_in_user_id'] = selected_id
            st.session_state['page'] = 'student_menu'
            st.rerun()
    else:
        st.warning("No students found in the database. Please contact admin.")
    
    if st.button("← Back to Main Menu", key="student_login_back"):
        st.session_state['page'] = 'main'
        st.rerun()

# --- STUDENT MENU PAGES ---

def student_menu():
    """The main menu for a logged-in student."""
    user_id = st.session_state['logged_in_user_id']
    if not user_id:
        st.session_state['page'] = 'main'
        st.rerun()
        
    student_name = execute_query("SELECT name FROM tbl_students WHERE id = %s", (user_id,), fetch_type='one')
    if student_name:
        student_name = student_name[0]

    st.sidebar.title(f"Welcome, {student_name}!")
    # Rerun kept here as it changes session state for navigation
    st.sidebar.button("Log Out", on_click=lambda: (st.session_state.update({'page': 'main', 'logged_in_user_id': None}), st.rerun()), use_container_width=True) 
    
    st.header("🎫 Student Event Dashboard")
    
    menu_choice = st.sidebar.radio(
        "Menu",
        ('My Registrations', 'Register for Event', 'Completed Events', 'Write Feedback', 'Cancel Registration')
    )
    st.divider()
    
    if menu_choice == 'Register for Event':
        display_register_event(user_id)
    elif menu_choice == 'My Registrations':
        display_my_registrations(user_id)
    elif menu_choice == 'Completed Events':
        display_list_completed_events(is_public=False)
    elif menu_choice == 'Write Feedback':
        display_write_event_feedback(user_id)
    elif menu_choice == 'Cancel Registration':
        display_cancel_registration(user_id)


def display_my_registrations(user_id):
    """(Student) Shows upcoming events the student is registered for."""
    st.subheader("🎫 My Upcoming Registrations")
    
    query = """
        SELECT e.id, e.name, e.date, e.start_time, v.name
        FROM tbl_event_participants p
        JOIN tbl_events e ON p.event_id = e.id
        LEFT JOIN tbl_venues v ON e.location_id = v.id
        WHERE p.user_id = %s
        AND CONCAT(e.date, ' ', e.end_time) > NOW()
        ORDER BY e.date
    """
    registrations = execute_query(query, (user_id,))
    
    if not registrations:
        st.info("You are not registered for any upcoming events.")
        return False

    reg_df = pd.DataFrame(registrations, columns=['Event ID', 'Event Name', 'Date', 'Start Time', 'Venue'])
    st.dataframe(reg_df, hide_index=True, use_container_width=True)
    return True 


def display_cancel_registration(user_id):
    """(Student) Cancels a registration for an event."""
    st.subheader("🚫 Cancel Registration")
    
    if not display_my_registrations(user_id):
        st.info("Nothing to cancel.")
        return

    st.warning("Cancellation will free up one ticket and remove your registration.")
    
    query = """
        SELECT e.id, e.name FROM tbl_event_participants p
        JOIN tbl_events e ON p.event_id = e.id
        WHERE p.user_id = %s
        AND CONCAT(e.date, ' ', e.end_time) > NOW()
        ORDER BY e.date
    """
    upcoming_events = execute_query(query, (user_id,))
    
    if not upcoming_events:
        st.info("No upcoming registrations found to cancel.")
        return
        
    event_options = {e[0]: e[1] for e in upcoming_events}

    selected_event_id = st.selectbox(
        "Select the Event to cancel:",
        options=list(event_options.keys()),
        format_func=lambda x: event_options[x],
        key="cancel_select"
    )

    if st.button("Confirm Cancellation", key="cancel_btn"):
        try:
            cursor = conn.cursor(buffered=True)
            
            sql_delete_part = "DELETE FROM tbl_event_participants WHERE event_id = %s AND user_id = %s"
            cursor.execute(sql_delete_part, (selected_event_id, user_id))
            
            sql_delete_order = """
                DELETE FROM tbl_orders 
                WHERE user_id = %s 
                AND ticket_id IN (SELECT id FROM tbl_tickets WHERE event_id = %s)
            """
            cursor.execute(sql_delete_order, (user_id, selected_event_id))
            
            sql_refund_ticket = "UPDATE tbl_tickets SET quantity = quantity + 1 WHERE event_id = %s ORDER BY id LIMIT 1"
            cursor.execute(sql_refund_ticket, (selected_event_id,))
            
            conn.commit()
            st.success(f"✅ Your registration for **{event_options[selected_event_id]}** has been cancelled. One ticket has been refunded to the pool.")
            # st.rerun() removed - rely on implicit rerun
            
        except mysql.connector.Error as err:
            conn.rollback()
            st.error(f"Error during cancellation: {err.msg}")
        except Exception as e:
            conn.rollback()
            st.error(f"Unexpected error: {e}")
        finally:
            cursor.close()


def display_register_event(user_id):
    """(Student) Handles ordering tickets and registering for an event."""
    st.subheader("🎟️ Register for a New Event")
    
    events = list_scheduled_events()
    if not events:
        st.info("No upcoming events are available for registration.")
        return

    event_options = {e[0]: f"{e[1]} at {e[6]}" for e in events}
    selected_event_id = st.selectbox(
        "Select an Event",
        options=list(event_options.keys()),
        format_func=lambda x: event_options[x]
    )

    if selected_event_id:
        st.info(f"Event: **{event_options[selected_event_id]}**")
        
        query_tickets = "SELECT id, ticket_type, price, quantity FROM tbl_tickets WHERE event_id = %s AND quantity > 0"
        tickets = execute_query(query_tickets, (selected_event_id,))

        if not tickets:
            st.warning("Sorry, no tickets are available for this event or it's sold out.")
            return

        ticket_map = {t[0]: t for t in tickets}
        ticket_options = {t[0]: f"{t[1]} - ${t[2]} (Available: {t[3]})" for t in tickets}

        selected_ticket_id = st.selectbox(
            "Select Ticket Type",
            options=list(ticket_options.keys()),
            format_func=lambda x: ticket_options[x]
        )
        
        if selected_ticket_id:
            ticket_info = ticket_map[selected_ticket_id]
            ticket_price = ticket_info[2]
            available_quantity = ticket_info[3]

            how_many = st.number_input(
                "How many tickets do you want to order?",
                min_value=1,
                max_value=available_quantity,
                value=1,
                key="ticket_qty_input"
            )
            
            total_price = ticket_price * how_many
            st.markdown(f"**Total Price: ${total_price:.2f}**")
            
            payment_status = 'Pending'
            if total_price > 0:
                payment_completed = st.checkbox("Simulate Payment Completed (Check to register immediately)")
                payment_status = 'Completed' if payment_completed else 'Pending'
            else:
                payment_status = 'Completed'
                st.info("This is a FREE ticket. Registration will be completed automatically.")

            if st.button("Confirm Order and Register", key="reg_btn"):
                sql_update_tickets = "UPDATE tbl_tickets SET quantity = quantity - %s WHERE id = %s"
                sql_order = "INSERT INTO tbl_orders (ticket_id, user_id, order_time, payment_status) VALUES (%s, %s, %s, %s)"
                order_time = datetime.datetime.now()
                order_records = [(selected_ticket_id, user_id, order_time, payment_status) for _ in range(how_many)]
                sql_register = "INSERT INTO tbl_event_participants (event_id, user_id, registration_time) VALUES (%s, %s, %s)"
                val_register = (selected_event_id, user_id, order_time)

                # --- TRANSACTION START ---
                try:
                    cursor = conn.cursor(buffered=True)
                    cursor.execute("SELECT quantity FROM tbl_tickets WHERE id = %s FOR UPDATE", (selected_ticket_id,))
                    current_qty = cursor.fetchone()[0]
                    if how_many > current_qty:
                         st.error("Error: Ticket quantity changed during selection. Please try again.")
                         conn.rollback()
                         return

                    cursor.execute(sql_update_tickets, (how_many, selected_ticket_id))
                    
                    for val in order_records:
                        cursor.execute(sql_order, val)

                    if payment_status == 'Completed':
                        try:
                            cursor.execute(sql_register, val_register)
                            st.success(f"✅ Successfully registered for the event! Tickets booked: {how_many}.")
                        except mysql.connector.Error as err:
                            if err.errno == errorcode.ER_DUP_ENTRY:
                                st.error("Error: You are ALREADY registered for this event.")
                            else:
                                raise 
                    else:
                        st.warning(f"⚠️ Order placed, but registration is pending. Complete payment to attend.")

                    conn.commit()

                except mysql.connector.Error as err:
                    conn.rollback()
                    st.error(f"❌ TRANSACTION FAILED. All changes rolled back. Database Error: {err.msg}")
                except Exception as e:
                    conn.rollback()
                    st.error(f"❌ UNEXPECTED TRANSACTION ERROR: {e}")
                finally:
                    cursor.close()
                # st.rerun() removed - rely on implicit rerun


def display_list_completed_events(is_public=False):
    """Fetches and displays all completed events."""
    st.subheader("🏁 Completed Events")
    
    query = """
        SELECT e.id, e.name, e.date, v.name AS venue_name, h.name AS host_name
        FROM tbl_events e
        LEFT JOIN tbl_venues v ON e.location_id = v.id
        LEFT JOIN tbl_hosts h ON e.organizer_id = h.id
        WHERE CONCAT(e.date, ' ', e.end_time) <= NOW()
        ORDER BY e.date DESC
    """
    events = execute_query(query)
    
    if not events:
        st.info("No completed events found.")
        return False

    event_df = pd.DataFrame(events, columns=['ID', 'Event Name', 'Date', 'Venue', 'Organizer'])
    st.dataframe(event_df, hide_index=True, use_container_width=True)
    
    if is_public or st.session_state['page'] == 'view_feedback_public':
        event_ids = [e[0] for e in events]
        
        selected_event_id = st.selectbox(
            "Select Event ID to view detailed summary:", 
            options=[None] + event_ids, 
            format_func=lambda x: "Select Event" if x is None else f"ID {x}",
            key="completed_summary_input"
        )
        
        if selected_event_id is not None:
            event_name = next((e[1] for e in events if e[0] == selected_event_id), None)
            if event_name:
                display_event_summary(event_name)
            else:
                st.warning("Invalid Event ID entered.")
    
    return True

def display_event_summary(event_name):
    """Calls the GetEventSummary stored procedure and displays results."""
    st.markdown(f"#### 📋 Summary for Event: {event_name}")
    try:
        cursor = conn.cursor(buffered=True)
        while cursor.nextset():
            pass

        cursor.callproc("GetEventSummary", [event_name])
        
        summary_data = []
        for result in cursor.stored_results():
            summary_data.extend(result.fetchall())
        
        if summary_data:
            summary = summary_data[0]
            st.write(f"📅 **Name:** {summary[0]}")
            st.write(f"🕒 **Date:** {summary[1]}")
            st.write(f"🏟️ **Venue:** {summary[2]}")
            st.write(f"👤 **Organizer:** {summary[3]}")
            st.write(f"👥 **Participants:** {summary[4]}")
        else:
            st.info("No summary data available for this event name.")
            
    except mysql.connector.Error as err:
        st.error(f"Error fetching event summary: {err.msg}")
    except Exception as e:
        st.error(f"Unexpected error in summary: {e}")
    finally:
        cursor.close()


def display_write_event_feedback(user_id):
    """(Student) Interface for writing event feedback."""
    st.subheader("✍️ Write Event Feedback")

    if not display_list_completed_events():
        st.info("No completed events available to review.")
        return

    event_options = execute_query("SELECT id, name FROM tbl_events WHERE CONCAT(date, ' ', end_time) <= NOW() ORDER BY date DESC")
    event_map = {e[0]: e[1] for e in event_options}

    event_id = st.selectbox(
        "Select the Event to review:",
        options=list(event_map.keys()),
        format_func=lambda x: event_map[x],
        key="feedback_event_select"
    )

    if event_id:
        # Show success message only once
        if st.session_state.get('feedback_status') == 'success' and st.session_state.get('feedback_event_id') == event_id:
            st.success("✅ Thank you! Your feedback has been submitted successfully.")
            st.session_state['feedback_status'] = None
        
        try:
            query_check_part = "SELECT attendance_status FROM tbl_event_participants WHERE event_id = %s AND user_id = %s"
            participant_record = execute_query(query_check_part, (event_id, user_id), fetch_type='one')
            
            if participant_record is None:
                st.error("Error: You were not a registered participant for this event.")
                return
            
            if participant_record[0] == 0:
                st.error("Error: Your attendance was not marked for this event.")
                return
                
            query_check_feedback = "SELECT id FROM tbl_event_feedback WHERE event_id = %s AND user_id = %s"
            feedback_record = execute_query(query_check_feedback, (event_id, user_id), fetch_type='one')
            
            if feedback_record is not None:
                st.info("You have already submitted feedback for this event.")
                return
                
            st.markdown("--- You are eligible to leave feedback! (Attended) ---")
            
            with st.form("feedback_form"):
                rating = st.slider("Enter rating (1-5)", min_value=1, max_value=5, value=5)
                comments = st.text_area("Enter comments (optional)")
                submitted = st.form_submit_button("Submit Feedback")

                if submitted:
                    sql_insert = """
                        INSERT INTO tbl_event_feedback (event_id, user_id, rating, comments, submitted_at) 
                        VALUES (%s, %s, %s, %s, %s)
                    """
                    val_insert = (event_id, user_id, rating, comments, datetime.datetime.now())
                    
                    result = commit_transaction(sql_insert, val_insert)
                    
                    if result is True:
                        st.session_state['feedback_status'] = 'success'
                        st.session_state['feedback_event_id'] = event_id
                        st.rerun() # Keep rerun here to reload the page and show success message
                    else:
                        st.error(f"Feedback submission failed: {result}")
                        
        except Exception as e:
            st.error(f"An unexpected error occurred: {e}")

def display_view_event_feedback():
    """(Public/Admin) Displays feedback and average rating using the SQL function."""
    st.subheader("📊 View Event Feedback")
    
    events = execute_query("SELECT id, name FROM tbl_events ORDER BY date DESC")
    if not events:
        st.info("No events available for feedback.")
        return

    event_map = {e[0]: e[1] for e in events}
    
    event_ids = [e[0] for e in events]
    selected_event_id = st.selectbox(
        "Select Event ID to view feedback:",
        options=[None] + event_ids,
        format_func=lambda x: event_map.get(x) if x is not None else "Select an Event",
        key="view_feedback_select"
    )

    if selected_event_id is not None:
        st.markdown(f"#### Feedback Report for **{event_map[selected_event_id]}**")
        
        query = """
            SELECT s.name, s.srn, f.rating, f.comments
            FROM tbl_event_feedback f
            JOIN tbl_students s ON f.user_id = s.id
            WHERE f.event_id = %s
        """
        feedback = execute_query(query, (selected_event_id,))

        if not feedback:
            st.info("No feedback found for this event yet.")
            return

        feedback_df = pd.DataFrame(feedback, columns=['Student Name', 'SRN', 'Rating', 'Comment'])
        st.dataframe(feedback_df, hide_index=True, use_container_width=True)

        try:
            cursor = conn.cursor(buffered=True)
            while cursor.nextset():
                pass
            cursor.execute("SELECT GetAverageRating(%s)", (selected_event_id,))
            avg_rating = cursor.fetchone()[0] or 0.0
            st.markdown(f"### ⭐ Average Rating: **{avg_rating:.2f}/5.00**")
        except mysql.connector.Error as err:
            st.error(f"Error calculating average rating: {err.msg}")
        except Exception as e:
            st.error(f"Unexpected error when fetching average rating: {e}")
        finally:
            cursor.close()

# --- ADMIN MENU PAGES ---

def admin_portal_menu():
    """The main menu for the Host/Admin."""
    st.sidebar.title("Host/Admin Menu")
    st.sidebar.button("Log Out", on_click=lambda: (st.session_state.update({'page': 'main', 'logged_in_user_id': None}), st.rerun()), use_container_width=True)
    
    st.header("🧑‍💼 Host & Admin Dashboard")
    
    menu_choice = st.sidebar.radio(
        "Admin Tasks",
        ('Add New Event', 'Update Event Details', 'Manage Event Tickets', 
         'Mark Event Attendance', 'View Participants', 
         'Add New Student', 'View Students/Hosts', 
         'Manage Venues', 'Manage Resources')
    )
    st.divider()

    if menu_choice == 'Add New Event':
        display_add_new_event()
    elif menu_choice == 'Update Event Details':
        display_update_event_details()
    elif menu_choice == 'Manage Event Tickets':
        display_manage_event_tickets()
    elif menu_choice == 'Mark Event Attendance':
        display_mark_attendance()
    elif menu_choice == 'View Participants':
        display_view_participants()
    elif menu_choice == 'Add New Student':
        display_add_new_student()
    elif menu_choice == 'View Students/Hosts':
        display_view_users()
    elif menu_choice == 'Manage Venues':
        display_manage_venues()
    elif menu_choice == 'Manage Resources':
        display_manage_resources()


def display_add_new_student():
    """(Admin) Interface for adding a new student."""
    st.subheader("🧑‍🎓 Add New Student")
    with st.form("add_student_form"):
        srn = st.text_input("Enter SRN (e.g., PES2UG23CS001)")
        name = st.text_input("Enter student name")
        semester = st.number_input("Enter semester (1-8)", min_value=1, max_value=8, value=1)
        section = st.text_input("Enter section (e.g., A)")
        submitted = st.form_submit_button("Add Student")
        
        if submitted:
            if not all([srn, name, section]):
                st.error("Please fill in all required fields.")
                return

            sql = "INSERT INTO tbl_students (srn, name, semester, section) VALUES (%s, %s, %s, %s)"
            val = (srn, name, semester, section)
            
            result = commit_transaction(sql, val)
            
            if result is True:
                st.success(f"✅ Successfully added student: **{name} ({srn})**")
                # st.rerun() removed - rely on implicit rerun
            elif isinstance(result, str):
                st.error(f"Failed to add student: {result}")


def display_add_new_event():
    """(Admin) Interface for adding a new event with checks."""
    st.subheader("🗓️ Add New Event")
    
    hosts = list_all_hosts()
    venues = list_available_venues()
    
    if not hosts: st.warning("No hosts available. Add a host first.")
    if not venues: st.warning("No available venues.")
    if not hosts or not venues: return

    host_map = {h[0]: f"{h[1]} ({h[3]})" for h in hosts}
    venue_map = {v[0]: f"{v[1]} ({v[3]} cap)" for v in venues}

    with st.form("add_event_form"):
        event_name = st.text_input("Event Name")
        description = st.text_area("Description")
        
        col_dt_1, col_dt_2, col_dt_3 = st.columns(3)
        with col_dt_1:
            date = st.date_input("Date", datetime.date.today())
        with col_dt_2:
            start_time = st.time_input("Start Time", datetime.time(10, 0))
        with col_dt_3:
            end_time = st.time_input("End Time", datetime.time(12, 0))

        organizer_id = st.selectbox("Select Host/Organizer", options=list(host_map.keys()), format_func=lambda x: host_map[x])
        location_id = st.selectbox("Select Venue", options=list(venue_map.keys()), format_func=lambda x: venue_map[x])
        
        venue_capacity = next((v[3] for v in venues if v[0] == location_id), 0)
        max_participants = st.number_input(f"Max Participants (Venue capacity: {venue_capacity})", min_value=1, max_value=venue_capacity, value=min(100, venue_capacity))

        submitted = st.form_submit_button("Schedule Event")

        if submitted:
            req_start_dt = datetime.datetime.combine(date, start_time)
            req_end_dt = datetime.datetime.combine(date, end_time)

            if req_end_dt <= req_start_dt:
                st.error("Error: Event end time must be after the start time.")
                return
            if max_participants > venue_capacity:
                st.error(f"❌ Error: Max participants ({max_participants}) cannot exceed venue capacity ({venue_capacity}).")
                return

            # Venue Time Conflict Check
            query_conflict = """
                SELECT id, name FROM tbl_events
                WHERE location_id = %s
                AND (CONCAT(date, ' ', start_time) < %s)
                AND (CONCAT(date, ' ', end_time) > %s)
            """
            conflicting_event = execute_query(query_conflict, (location_id, req_end_dt, req_start_dt), fetch_type='one')
            
            if conflicting_event:
                st.error(f"❌ CONFLICT: Venue booked for '{conflicting_event[1]}'.")
                return

            sql_insert = """
                INSERT INTO tbl_events 
                (name, description, date, start_time, end_time, location_id, organizer_id, status, max_participants)
                VALUES (%s, %s, %s, %s, %s, %s, %s, 'Scheduled', %s)
            """
            val_insert = (event_name, description, date, start_time, end_time, location_id, organizer_id, max_participants)
            
            result = commit_transaction(sql_insert, val_insert)
            
            if result is True:
                st.success(f"✅ Success! Event **'{event_name}'** scheduled.")
                # st.rerun() removed - rely on implicit rerun
            elif isinstance(result, str):
                st.error(f"Failed to add event: {result}")


def display_update_event_details():
    """(Admin) Interface for updating event details."""
    st.subheader("✏️ Update Event Details")
    
    events = list_scheduled_events()
    if not events:
        st.info("No upcoming events to update.")
        return

    event_map = {e[0]: f"{e[1]} at {e[6]}" for e in events}
    selected_event_id = st.selectbox("Select Event to Update:", options=list(event_map.keys()), format_func=lambda x: event_map[x], key="update_event_select")
    
    current_event = next((e for e in events if e[0] == selected_event_id), None)
    if not current_event: return

    cursor = conn.cursor(buffered=True)
    cursor.execute("SELECT * FROM tbl_events WHERE id = %s", (selected_event_id,))
    full_event = cursor.fetchone()
    cursor.close()
    if not full_event: return
    
    try:
        (e_id, e_name, e_desc, e_date, e_start, e_end, e_loc_id, e_org_id, e_status, e_max_part, *extra_columns) = full_event
    except ValueError:
        st.error(f"Database schema mismatch: Expected at least 10 columns in tbl_events. Found {len(full_event)}.")
        return
    
    current_start_time = convert_to_time(e_start)
    current_end_time = convert_to_time(e_end)

    st.markdown(f"**Updating:** {e_name} (ID: {e_id})")

    with st.form("update_form"):
        st.markdown("#### Update Name/Description")
        new_name = st.text_input("New Name", value=e_name)
        new_desc = st.text_area("New Description", value=e_desc)
        
        st.markdown("#### Update Date/Time")
        col_dt_1, col_dt_2, col_dt_3 = st.columns(3)
        with col_dt_1:
            new_date = st.date_input("New Date", value=e_date)
        with col_dt_2:
            new_start_time = st.time_input("New Start Time", value=current_start_time)
        with col_dt_3:
            new_end_time = st.time_input("New End Time", value=current_end_time)

        st.markdown("#### Update Location")
        venues = list_available_venues()
        venue_map = {v[0]: f"{v[1]} ({v[3]} cap)" for v in venues}
        
        current_venue_index = list(venue_map.keys()).index(e_loc_id) if e_loc_id in list(venue_map.keys()) else 0
        
        new_location_id = st.selectbox(
            "New Venue", 
            options=list(venue_map.keys()), 
            format_func=lambda x: venue_map[x], 
            index=current_venue_index
        )

        submitted = st.form_submit_button("Apply Updates") 
        
        if submitted:
            updates = []
            params = []
            
            if new_name != e_name:
                updates.append("name = %s")
                params.append(new_name)
            if new_desc != e_desc:
                updates.append("description = %s")
                params.append(new_desc)
                
            if new_date != e_date or new_start_time != current_start_time or new_end_time != current_end_time:
                req_start_dt = datetime.datetime.combine(new_date, new_start_time)
                req_end_dt = datetime.datetime.combine(new_date, new_end_time)
                
                if req_end_dt <= req_start_dt:
                    st.error("Error: End time must be after start time.")
                    return
                
                query_conflict = """
                    SELECT id, name FROM tbl_events
                    WHERE location_id = %s
                    AND id != %s
                    AND (CONCAT(date, ' ', start_time) < %s)
                    AND (CONCAT(date, ' ', end_time) > %s)
                """
                conflicting_event = execute_query(query_conflict, (e_loc_id, e_id, req_end_dt, req_start_dt), fetch_type='one')
                if conflicting_event:
                    st.error(f"❌ CONFLICT: New time overlaps with another event at current location.")
                    return
                
                updates.extend(["date = %s", "start_time = %s", "end_time = %s"])
                params.extend([new_date, new_start_time, new_end_time])
                
            if new_location_id != e_loc_id:
                new_capacity = next((v[3] for v in venues if v[0] == new_location_id), 0)
                if e_max_part > new_capacity:
                    st.error(f"❌ Error: Event max participants ({e_max_part}) exceeds new venue capacity ({new_capacity}).")
                    return
                    
                event_start_dt = datetime.datetime.combine(new_date, new_start_time)
                event_end_dt = datetime.datetime.combine(new_date, new_end_time)
                
                query_conflict_new = """
                    SELECT id, name FROM tbl_events
                    WHERE location_id = %s
                    AND id != %s
                    AND (CONCAT(date, ' ', start_time) < %s)
                    AND (CONCAT(date, ' ', end_time) > %s)
                """
                conflicting_event_new = execute_query(query_conflict_new, (new_location_id, e_id, event_end_dt, event_start_dt), fetch_type='one')
                if conflicting_event_new:
                    st.error("❌ CONFLICT: The new venue is booked by another event at this time.")
                    return
                    
                updates.append("location_id = %s")
                params.append(new_location_id)

            if not updates:
                st.info("No changes specified.")
                return

            params.append(e_id)
            sql_update = f"UPDATE tbl_events SET {', '.join(updates)} WHERE id = %s"
            result = commit_transaction(sql_update, tuple(params))
            
            if result is True:
                st.success("✅ Event details updated successfully.")
                # st.rerun() removed - rely on implicit rerun
            else:
                st.error(f"Update failed: {result}")


def display_manage_event_tickets():
    """(Admin) Interface for managing event tickets."""
    st.subheader("🎫 Manage Event Tickets")
    
    events = execute_query("SELECT id, name FROM tbl_events")
    if not events: st.info("No events to manage tickets for.")
    event_map = {e[0]: e[1] for e in events}
    
    event_id = st.selectbox("Select Event:", options=list(event_map.keys()), format_func=lambda x: event_map[x], key="ticket_event_select")
    
    if event_id:
        st.markdown("##### Existing Tickets")
        query_tickets = "SELECT id, ticket_type, price, quantity FROM tbl_tickets WHERE event_id = %s"
        tickets = execute_query(query_tickets, (event_id,))
        
        if tickets:
            ticket_df = pd.DataFrame(tickets, columns=['ID', 'Type', 'Price', 'Quantity'])
            st.dataframe(ticket_df, hide_index=True)
        else:
            st.info("No tickets defined for this event yet.")
            
        st.markdown("---")
        
        mode = st.radio("Action:", ('Add New Ticket Type', 'Update Existing Ticket'), key="ticket_action")
        
        if mode == 'Add New Ticket Type':
            with st.form("add_ticket_form"):
                ticket_type = st.text_input("New Ticket Type Name (e.g., Early Bird)")
                price = st.number_input("Price", min_value=0.0, step=0.01)
                quantity = st.number_input("Total Quantity Available", min_value=0, step=1)
                submitted = st.form_submit_button("Add New Ticket")
                
                if submitted:
                    sql_insert = "INSERT INTO tbl_tickets (event_id, ticket_type, price, quantity) VALUES (%s, %s, %s, %s)"
                    result = commit_transaction(sql_insert, (event_id, ticket_type, price, quantity))
                    if result is True:
                        st.success(f"✅ New ticket type '{ticket_type}' added.")
                        # st.rerun() removed - rely on implicit rerun
                    else:
                        st.error(f"Failed to add ticket: {result}")

        elif mode == 'Update Existing Ticket' and tickets:
            ticket_map = {t[0]: t[1] for t in tickets}
            ticket_id = st.selectbox("Select Ticket ID to Update:", options=list(ticket_map.keys()), format_func=lambda x: f"ID {x}: {ticket_map[x]}")
            
            with st.form("update_ticket_form"):
                current_ticket = next(t for t in tickets if t[0] == ticket_id)
                new_price = st.number_input(f"New Price (Current: ${current_ticket[2]}): Set to -1 to skip", min_value=-1.0, value=-1.0, step=0.01)
                new_qty = st.number_input(f"New Total Quantity (Current: {current_ticket[3]}): Set to -1 to skip", min_value=-1, value=-1, step=1)
                
                submitted = st.form_submit_button("Update Ticket")
                
                if submitted:
                    updates = []
                    params = []
                    if new_price >= 0:
                        updates.append("price = %s")
                        params.append(new_price)
                    if new_qty >= 0:
                        updates.append("quantity = %s")
                        params.append(new_qty)
                        
                    if not updates:
                        st.info("No changes specified.")
                        return

                    params.append(ticket_id)
                    params.append(event_id)
                    sql_update = f"UPDATE tbl_tickets SET {', '.join(updates)} WHERE id = %s AND event_id = %s"
                    
                    result = commit_transaction(sql_update, tuple(params))
                    if result is True:
                        st.success(f"✅ Ticket ID {ticket_id} updated.")
                        # st.rerun() removed - rely on implicit rerun
                    else:
                        st.error(f"Update failed: {result}")


def display_mark_attendance():
    """(Admin) Interface for marking event attendance."""
    st.subheader("🧑‍💼 Mark Event Attendance")
    
    events = execute_query("SELECT id, name, date FROM tbl_events ORDER BY date DESC")
    if not events: st.info("No events found.")
    event_map = {e[0]: f"{e[1]} ({e[2]})" for e in events}
    
    event_id = st.selectbox("Select Event:", options=list(event_map.keys()), format_func=lambda x: event_map[x], key="attendance_event_select")
    
    if event_id:
        query = """
            SELECT s.id, s.name, s.srn, p.attendance_status
            FROM tbl_event_participants p
            JOIN tbl_students s ON p.user_id = s.id
            WHERE p.event_id = %s
            ORDER BY s.name
        """
        participants = execute_query(query, (event_id,))
        
        if not participants:
            st.info("No students are registered for this event.")
            return

        st.markdown(f"##### Registered Students for **{event_map[event_id]}**")
        part_df = pd.DataFrame(participants, columns=['ID', 'Name', 'SRN', 'Attended?'])
        part_df['Attended?'] = part_df['Attended?'].apply(lambda x: 'Yes' if x == 1 else 'No')
        st.dataframe(part_df, hide_index=True, use_container_width=True)

        with st.form("mark_attendance_form"):
            student_map = {p[0]: f"{p[1]} ({p[2]})" for p in participants}
            user_id_to_mark = st.selectbox("Select Student ID to mark as 'Attended':", options=list(student_map.keys()), format_func=lambda x: student_map[x])
            submitted = st.form_submit_button("Mark Attended (1)")

            if submitted:
                sql_update = "UPDATE tbl_event_participants SET attendance_status = 1 WHERE event_id = %s AND user_id = %s"
                result = commit_transaction(sql_update, (event_id, user_id_to_mark))
                
                if result is True:
                    st.success(f"✅ Successfully marked Student {user_id_to_mark} as attended.")
                    # st.rerun() removed - rely on implicit rerun
                elif isinstance(result, str):
                    st.error(f"Failed to mark attendance: {result}")


def display_view_participants():
    """(Admin) Interface for viewing participant details and counts."""
    st.subheader("👥 View Event Participants")
    
    mode = st.radio("View Mode:", ('Detailed List', 'Participant Counts Summary'), key="part_view_mode")
    
    if mode == 'Detailed List':
        st.markdown("##### All Event Participants (Detailed)")
        query = """
            SELECT e.name, s.name, s.srn, p.registration_time, p.attendance_status
            FROM tbl_event_participants p
            JOIN tbl_events e ON p.event_id = e.id
            JOIN tbl_students s ON p.user_id = s.id
            ORDER BY e.name, s.name
        """
        records = execute_query(query)
        
        if records:
            part_df = pd.DataFrame(records, columns=['Event Name', 'Student Name', 'SRN', 'Registration Time', 'Attended?'])
            part_df['Attended?'] = part_df['Attended?'].apply(lambda x: 'Yes' if x == 1 else 'No')
            st.dataframe(part_df, hide_index=True, use_container_width=True)
        else:
            st.info("No participant records found.")
            
    elif mode == 'Participant Counts Summary':
        st.markdown("##### Participant Count by Event (Summary)")
        query = """
            SELECT e.name, COUNT(p.user_id) AS participant_count
            FROM tbl_event_participants p
            JOIN tbl_events e ON p.event_id = e.id
            GROUP BY p.event_id, e.name
            ORDER BY participant_count DESC
        """
        records = execute_query(query)
        
        if records:
            count_df = pd.DataFrame(records, columns=['Event Name', 'Total Registered'])
            st.dataframe(count_df, hide_index=True, use_container_width=True)
        else:
            st.info("No participant records found.")


def display_view_users():
    """(Admin) Interface for viewing all students and hosts."""
    st.subheader("👤 User Management")
    
    mode = st.radio("View:", ('All Students', 'All Hosts', 'Add New Host'), key="user_view_mode")
    
    if mode == 'All Students':
        st.markdown("##### 🧑‍🎓 All Students")
        students = execute_query("SELECT id, srn, name, semester, section FROM tbl_students ORDER BY name")
        if students:
            student_df = pd.DataFrame(students, columns=['ID', 'SRN', 'Name', 'Semester', 'Section'])
            st.dataframe(student_df, hide_index=True, use_container_width=True)
        else:
            st.info("No students found.")
            
    elif mode == 'All Hosts':
        st.markdown("##### 🧑‍💼 All Hosts")
        hosts = list_all_hosts()
        if hosts:
            host_df = pd.DataFrame(hosts, columns=['ID', 'Name', 'Department', 'Role'])
            st.dataframe(host_df, hide_index=True, use_container_width=True)
        else:
            st.info("No hosts found.")
            
    elif mode == 'Add New Host':
        st.markdown("##### 🧑‍💼 Add New Host")
        with st.form("add_host_form"):
            name = st.text_input("Host Name")
            email = st.text_input("Host Email")
            phone = st.text_input("Host Phone (optional)")
            role = st.text_input("Host Role (e.g., Professor)")
            department = st.text_input("Host Department (optional)")
            submitted = st.form_submit_button("Add Host")
            
            if submitted:
                sql_insert = "INSERT INTO tbl_hosts (name, email, phone, role, department) VALUES (%s, %s, %s, %s, %s)"
                val_insert = (name, email, phone if phone else None, role, department if department else None)
                
                result = commit_transaction(sql_insert, val_insert)
                
                if result is True:
                    st.success(f"✅ Success! Host '{name}' has been added.")
                    # st.rerun() removed - rely on implicit rerun
                elif isinstance(result, str):
                    st.error(f"Failed to add host: {result}")


def display_manage_venues():
    """(Admin) Interface for viewing and toggling venue availability."""
    st.subheader("🏟️ Manage Venues")
    
    venues = list_all_venues()
    if not venues:
        st.info("No venues found.")
        return

    st.markdown("##### All Venues (Current Status)")
    venue_df = pd.DataFrame(venues, columns=['ID', 'Name', 'Building', 'Capacity', 'Available'])
    venue_df['Available'] = venue_df['Available'].apply(lambda x: 'Available' if x == 1 else 'Not Available')
    st.dataframe(venue_df, hide_index=True, use_container_width=True)

    st.markdown("---")
    st.markdown("##### 🔄 Update Venue Availability")
    
    with st.form("update_venue_form"):
        venue_map = {v[0]: v[1] for v in venues}
        
        venue_id = st.selectbox("Select Venue ID to update:", options=list(venue_map.keys()), format_func=lambda x: f"ID {x}: {venue_map[x]}")
        
        current_status = next((v[4] for v in venues if v[0] == venue_id), 0)

        new_status = st.radio("New Status:", (1, 0), format_func=lambda x: "Available" if x == 1 else "Not Available", index=0 if current_status == 1 else 1)
        submitted = st.form_submit_button("Update Status")

        if submitted:
            sql_update = "UPDATE tbl_venues SET is_available = %s WHERE id = %s"
            result = commit_transaction(sql_update, (new_status, venue_id))
            
            if result is True:
                st.success(f"✅ Venue ID {venue_id} availability updated to {'Available' if new_status == 1 else 'Not Available'}.")
                # st.rerun() removed - rely on implicit rerun
            elif isinstance(result, str):
                st.error(f"Update failed: {result}")


def display_manage_resources():
    """(Admin) Interface for managing resources (Add, Status, Maintenance, Booking, Cleanup)."""
    st.subheader("📦 Resource Management")
    
    # 1. Resource List
    st.markdown("##### All Resources")
    resources = list_all_resources()
    if resources:
        resource_df = pd.DataFrame(resources, columns=['ID', 'Name', 'Type', 'Total Qty', 'Status'])
        st.dataframe(resource_df, hide_index=True, use_container_width=True)
    else:
        st.info("No resources found.")

    st.markdown("---")
    
    # 2. Cleanup & Status
    if st.button("🧹 Run Resource Cleanup (Replenish Expired Bookings)", key="cleanup_btn"):
        try:
            cursor = conn.cursor(buffered=True)
            conn.autocommit = False 

            st.spinner("Calling ReplenishResources()...")
            while cursor.nextset():
                pass
            
            cursor.callproc("ReplenishResources")
            for result in cursor.stored_results():
                result.fetchall() 

            expired_count = execute_query("SELECT COUNT(*) FROM tbl_event_resources WHERE booking_end < NOW();", fetch_type='one')[0]
            if expired_count > 0:
                cursor.execute("DELETE FROM tbl_event_resources WHERE booking_end < NOW();")
                conn.commit()
                st.success(f"🧹 Cleaned up {expired_count} expired assignments and resources replenished.")
            else:
                conn.commit()
                st.success("✅ No expired event-resource mappings found to delete/replenish.")
        except Exception as e:
            conn.rollback()
            st.error(f"❌ Database error during cleanup: {e}")
        finally:
            conn.autocommit = True
            st.rerun() # Keep rerun here to reload the resource list and cleanup message

    st.markdown("---")
    
    # 3. Resource Actions
    action = st.radio("Resource Action:", ('Add New Resource', 'Update Status', 'Schedule Maintenance', 'Book for Event'), key="resource_action")
    
    if action == 'Add New Resource':
        with st.form("add_resource_form"):
            name = st.text_input("Resource Name")
            type_res = st.text_input("Type (e.g., AV Equipment)")
            quantity = st.number_input("Total Quantity", min_value=1, step=1)
            description = st.text_area("Description")
            submitted = st.form_submit_button("Add Resource")
            
            if submitted:
                sql_insert = "INSERT INTO tbl_resources (name, type, quantity, description, is_available, maintenance_status) VALUES (%s, %s, %s, %s, 1, 'Available')"
                val_insert = (name, type_res, quantity, description)
                result = commit_transaction(sql_insert, val_insert)
                if result is True:
                    st.success(f"✅ Success! Resource '{name}' added.")
                    # st.rerun() removed - rely on implicit rerun
                else:
                    st.error(f"Failed to add resource: {result}")

    elif action == 'Update Status' and resources:
        with st.form("update_resource_status_form"):
            resource_map = {r[0]: r[1] for r in resources}
            resource_id = st.selectbox("Select Resource to update:", options=list(resource_map.keys()), format_func=lambda x: f"ID {x}: {resource_map[x]}")
            new_status = st.text_input("New Maintenance Status (e.g., Available, Under Maintenance)")
            submitted = st.form_submit_button("Update Status")

            if submitted:
                is_available = 1 if new_status.lower() == 'available' else 0
                sql_update = "UPDATE tbl_resources SET maintenance_status = %s, is_available = %s WHERE id = %s"
                result = commit_transaction(sql_update, (new_status, is_available, resource_id))
                
                if result is True:
                    st.success(f"✅ Resource ID {resource_id} status updated.")
                    # st.rerun() removed - rely on implicit rerun
                elif isinstance(result, str):
                    st.error(f"Update failed: {result}")

    elif action == 'Schedule Maintenance' and resources:
        with st.form("schedule_maintenance_form"):
            resource_map = {r[0]: r[1] for r in resources}
            resource_id = st.selectbox("Select Resource for Maintenance:", options=list(resource_map.keys()), format_func=lambda x: f"ID {x}: {resource_map[x]}")
            
            st.markdown("Enter maintenance start and end times in **YYYY-MM-DD HH:MM:SS** format.")
            col_m_1, col_m_2 = st.columns(2)
            with col_m_1:
                start_dt = st.text_input("Start Time (e.g., 2025-11-20 09:00:00)", key="m_start")
            with col_m_2:
                end_dt = st.text_input("End Time (e.g., 2025-11-20 17:00:00)", key="m_end")
            description = st.text_area("Maintenance Description")
            submitted = st.form_submit_button("Schedule Maintenance")

            if submitted:
                try:
                    req_start = datetime.datetime.strptime(start_dt, '%Y-%m-%d %H:%M:%S')
                    req_end = datetime.datetime.strptime(end_dt, '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    st.error("Invalid date/time format. Use YYYY-MM-DD HH:MM:SS.")
                    return
                
                if req_end <= req_start:
                    st.error("Error: Maintenance end time must be after the start time.")
                    return

                query_conflict = """
                    SELECT e.name FROM tbl_event_resources er
                    JOIN tbl_events e ON er.event_id = e.id
                    WHERE er.resource_id = %s
                    AND (er.booking_start < %s) AND (er.booking_end > %s)
                """
                conflicting_booking = execute_query(query_conflict, (resource_id, req_end, req_start), fetch_type='one')
                
                if conflicting_booking:
                    st.error(f"❌ CONFLICT: Resource booked for '{conflicting_booking[0]}' during this time.")
                    return

                sql_insert = "INSERT INTO tbl_resource_maintenance (resource_id, maintenance_start, maintenance_end, description) VALUES (%s, %s, %s, %s)"
                sql_update = "UPDATE tbl_resources SET is_available = 0, maintenance_status = 'Under Maintenance' WHERE id = %s"
                
                try:
                    cursor = conn.cursor(buffered=True)
                    cursor.execute(sql_insert, (resource_id, req_start, req_end, description))
                    cursor.execute(sql_update, (resource_id,))
                    conn.commit()
                    st.success("✅ Success! Maintenance scheduled and status updated.")
                    # st.rerun() removed - rely on implicit rerun
                except mysql.connector.Error as err:
                    conn.rollback()
                    st.error(f"An error occurred: {err.msg}")
                finally:
                    cursor.close()

    elif action == 'Book for Event' and resources:
        events_upcoming = execute_query("SELECT id, name FROM tbl_events WHERE CONCAT(date, ' ', end_time) > NOW()")
        if not events_upcoming: st.info("No upcoming events to book resources for.")
        
        with st.form("book_resource_form"):
            event_map = {e[0]: e[1] for e in events_upcoming}
            resource_map = {r[0]: f"{r[1]} (Qty: {r[3]})" for r in resources if r[4].lower() == 'available'}

            event_id = st.selectbox("Select Event:", options=list(event_map.keys()), format_func=lambda x: event_map[x])
            resource_id = st.selectbox("Select Available Resource:", options=list(resource_map.keys()), format_func=lambda x: resource_map[x])
            
            current_qty = next((r[3] for r in resources if r[0] == resource_id), 0)
            quantity_to_book = st.number_input(f"Quantity to Book (Max: {current_qty}):", min_value=1, max_value=current_qty, step=1)

            st.markdown("Enter booking start and end times in **YYYY-MM-DD HH:MM:SS** format.")
            col_b_1, col_b_2 = st.columns(2)
            with col_b_1:
                book_start_str = st.text_input("Start Time (e.g., 2025-11-20 09:00:00)", key="b_start")
            with col_b_2:
                book_end_str = st.text_input("End Time (e.g., 2025-11-20 17:00:00)", key="b_end")
            submitted = st.form_submit_button("Confirm Booking")

            if submitted:
                try:
                    req_start = datetime.datetime.strptime(book_start_str, '%Y-%m-%d %H:%M:%S')
                    req_end = datetime.datetime.strptime(book_end_str, '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    st.error("Invalid date/time format. Use YYYY-MM-DD HH:MM:SS.")
                    return

                if req_end <= req_start:
                    st.error("Error: End time must be after start time.")
                    return
                
                insert_query = """
                    INSERT INTO tbl_event_resources (event_id, resource_id, quantity_booked, booking_start, booking_end)
                    VALUES (%s, %s, %s, %s, %s)
                """
                
                try:
                    cursor = conn.cursor(buffered=True)
                    conn.autocommit = False 
                    
                    lock_query = "SELECT quantity FROM tbl_resources WHERE id = %s FOR UPDATE"
                    cursor.execute(lock_query, (resource_id,))
                    locked_qty = cursor.fetchone()[0]
                    if quantity_to_book > locked_qty:
                        conn.rollback()
                        st.error("Error: Quantity is no longer available. Rolling back.")
                        return

                    cursor.execute(insert_query, (event_id, resource_id, quantity_to_book, req_start, req_end))
                    conn.commit()
                    st.success("✅ Booking successful! Resource availability updated automatically (via trigger).")
                    # st.rerun() removed - rely on implicit rerun
                except mysql.connector.Error as err:
                    conn.rollback()
                    st.error(f"❌ Booking failed (likely conflict/lack of stock): {err.msg}")
                finally:
                    conn.autocommit = True


# --- MAIN APP LOGIC ---

def run_app():
    """Switches between different pages based on session state."""
    if st.session_state['page'] == 'main':
        main_menu()
    elif st.session_state['page'] == 'student_login':
        student_login_page()
    elif st.session_state['page'] == 'student_menu':
        student_menu()
    elif st.session_state['page'] == 'admin_portal':
        admin_portal_menu()
    elif st.session_state['page'] == 'view_feedback_public':
        display_view_event_feedback()
        if st.button("← Back to Main Menu"):
            st.session_state['page'] = 'main'
            st.rerun()
    
# Run the Streamlit App
if __name__ == "__main__":
    run_app()