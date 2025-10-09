--DDL Commands 

-- Table for Venues
CREATE TABLE tbl_venues (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    building VARCHAR(100) NOT NULL,
    floor INT NOT NULL,
    capacity INT NOT NULL,
    description TEXT,
    is_available TINYINT(1) DEFAULT 1 NOT NULL,
    CONSTRAINT chk_capacity CHECK (capacity > 0)
);

-- Table for Hosts/Organizers
CREATE TABLE tbl_hosts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    phone VARCHAR(20) UNIQUE,
    role VARCHAR(100) NOT NULL,
    department VARCHAR(100)
);

-- Table for Events
CREATE TABLE tbl_events (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    date DATE NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    location_id INT,
    organizer_id INT NOT NULL,
    status VARCHAR(50) DEFAULT 'Scheduled' NOT NULL,
    max_participants INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_status CHECK (status IN ('Scheduled','Cancelled','Completed','Postponed')),
    CONSTRAINT chk_end_time CHECK (end_time > start_time),
    CONSTRAINT fk_venue FOREIGN KEY (location_id) REFERENCES tbl_venues(id) ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT fk_host FOREIGN KEY (organizer_id) REFERENCES tbl_hosts(id) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT chk_max_participants CHECK (max_participants > 0)
);

-- Table for Students
CREATE TABLE tbl_students (
    id INT AUTO_INCREMENT PRIMARY KEY,
    srn VARCHAR(20) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    semester INT NOT NULL,
    section VARCHAR(5) NOT NULL,
    CONSTRAINT chk_semester CHECK (semester BETWEEN 1 AND 8)
);

-- Table for Tickets
CREATE TABLE tbl_tickets (
    id INT AUTO_INCREMENT PRIMARY KEY,
    event_id INT NOT NULL,
    ticket_type VARCHAR(100) NOT NULL,
    price DECIMAL(10,2) NOT NULL,
    quantity INT NOT NULL,
    issued_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_event_ticket FOREIGN KEY (event_id) REFERENCES tbl_events(id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT chk_price CHECK (price >= 0),
    CONSTRAINT chk_quantity CHECK (quantity >= 0)
);

-- Table for Orders
CREATE TABLE tbl_orders (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ticket_id INT NOT NULL,
    user_id INT NOT NULL,
    order_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    payment_status VARCHAR(50) DEFAULT 'Pending' NOT NULL,
    CONSTRAINT fk_ticket_order FOREIGN KEY (ticket_id) REFERENCES tbl_tickets(id) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_student_order FOREIGN KEY (user_id) REFERENCES tbl_students(id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT chk_payment_status CHECK (payment_status IN ('Pending','Completed','Failed'))
);

-- Table for Event Participants
CREATE TABLE tbl_event_participants (
    id INT AUTO_INCREMENT PRIMARY KEY,
    event_id INT NOT NULL,
    user_id INT NOT NULL,
    registration_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    attendance_status TINYINT(1) DEFAULT 0 NOT NULL,
    CONSTRAINT fk_event_participant FOREIGN KEY (event_id) REFERENCES tbl_events(id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_student_participant FOREIGN KEY (user_id) REFERENCES tbl_students(id) ON DELETE CASCADE ON UPDATE CASCADE,
    UNIQUE (event_id, user_id)
);

-- Table for Event Feedback
CREATE TABLE tbl_event_feedback (
    id INT AUTO_INCREMENT PRIMARY KEY,
    event_id INT NOT NULL,
    user_id INT,
    rating INT,
    comments TEXT,
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_event_feedback FOREIGN KEY (event_id) REFERENCES tbl_events(id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_student_feedback FOREIGN KEY (user_id) REFERENCES tbl_students(id) ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT chk_rating CHECK (rating BETWEEN 1 AND 5),
    UNIQUE(event_id, user_id)
);

-- Table for Resources
CREATE TABLE tbl_resources (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    type VARCHAR(100),
    quantity INT NOT NULL,
    description TEXT,
    is_available TINYINT(1) DEFAULT 1 NOT NULL,
    maintenance_status VARCHAR(100) DEFAULT 'Available' NOT NULL,
    CONSTRAINT chk_quantity_resource CHECK (quantity >= 0)
);

-- Table for linking Events and Resources
CREATE TABLE tbl_event_resources (
    id INT AUTO_INCREMENT PRIMARY KEY,
    event_id INT NOT NULL,
    resource_id INT NOT NULL,
    quantity_booked INT NOT NULL,
    booking_start TIMESTAMP NOT NULL,
    booking_end TIMESTAMP NOT NULL,
    CONSTRAINT fk_event_resource FOREIGN KEY (event_id) REFERENCES tbl_events(id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_resource_event FOREIGN KEY (resource_id) REFERENCES tbl_resources(id) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT chk_booking_end CHECK (booking_end > booking_start),
    CONSTRAINT chk_quantity_booked CHECK (quantity_booked > 0)
);

-- Table for Resource Maintenance
CREATE TABLE tbl_resource_maintenance (
    id INT AUTO_INCREMENT PRIMARY KEY,
    resource_id INT NOT NULL,
    maintenance_start TIMESTAMP NOT NULL,
    maintenance_end TIMESTAMP,
    description TEXT,
    performed_by VARCHAR(255),
    CONSTRAINT fk_resource_maintenance FOREIGN KEY (resource_id) REFERENCES tbl_resources(id) ON DELETE CASCADE ON UPDATE CASCADE
);


--DML Commands

-- Insert into tbl_venues
INSERT INTO tbl_venues (name, building, floor, capacity, description, is_available) VALUES
('Auditorium', 'Block 5', 0, 500, 'Main auditorium with projector and sound system', 1),
('Seminar Hall 1', 'Block 2', 1, 100, 'Smaller hall for seminars and workshops', 1),
('Open Air Theatre', 'Campus Center', 0, 1000, 'Outdoor venue for large events', 1),
('CSE Lab 101', 'Block 5', 1, 60, 'Computer lab for technical workshops', 0),
('Library Reading Hall', 'Block 8', 2, 200, 'Quiet zone, suitable for talks', 1);

-- Insert into tbl_hosts
INSERT INTO tbl_hosts (name, email, phone, role, department) VALUES
('Dr. Ramesh Kumar', 'ramesh.k@pesu.ac.in', '9876543210', 'Professor', 'Computer Science'),
('Smt. Sunita Sharma', 'sunita.s@pesu.ac.in', '9876543211', 'Event Coordinator', 'Admin'),
('Ananya Gupta', 'ananya.g@pesu.ac.in', '9876543212', 'Student Council President', 'Student Council'),
('Dr. Vikram Singh', 'vikram.s@pesu.ac.in', '9876543213', 'HOD', 'Mechanical Engineering'),
('Priya Reddy', 'priya.r@pesu.ac.in', '9876543214', 'Cultural Secretary', 'Student Council');

-- Insert into tbl_events
INSERT INTO tbl_events (name, description, date, start_time, end_time, location_id, organizer_id, status, max_participants) VALUES
('Hackathon 2025', 'A 24-hour coding competition', '2025-10-20', '09:00:00', '17:00:00', 1, 1, 'Scheduled', 200),
('Guest Lecture on AI', 'Talk by an industry expert on modern AI trends', '2025-11-05', '11:00:00', '13:00:00', 2, 1, 'Scheduled', 100),
('Annual Cultural Fest', 'Maaya 2025 - University cultural festival', '2025-12-15', '10:00:00', '22:00:00', 3, 3, 'Scheduled', 1000),
('Robotics Workshop', 'Hands-on workshop on building autonomous robots', '2025-10-25', '10:00:00', '16:00:00', 4, 4, 'Completed', 50),
('Literary Debate', 'Inter-departmental debate competition', '2025-11-12', '14:00:00', '16:00:00', 5, 5, 'Scheduled', 80);

-- Insert into tbl_students
INSERT INTO tbl_students (srn, name, semester, section) VALUES
('PES2UG23CS001', 'Arjun Sharma', 3, 'A'),
('PES2UG23EC002', 'Meera Iyer', 3, 'B'),
('PES2UG22CS101', 'Rohan Das', 5, 'C'),
('PES2UG22ME055', 'Priya Singh', 5, 'A'),
('PES2UG24CS200', 'Sameer Khan', 1, 'D');

-- Insert into tbl_tickets
INSERT INTO tbl_tickets (event_id, ticket_type, price, quantity) VALUES
(1, 'Participant Pass', 100.00, 200),
(2, 'Free Entry', 0.00, 100),
(3, 'General Admission', 250.00, 1000),
(4, 'Workshop Kit Included', 500.00, 50),
(3, 'VIP Pass', 1000.00, 50);

-- Insert into tbl_orders
INSERT INTO tbl_orders (ticket_id, user_id, payment_status) VALUES
(1, 1, 'Completed'),
(3, 2, 'Completed'),
(4, 3, 'Completed'),
(3, 4, 'Pending'),
(5, 5, 'Completed');

-- Insert into tbl_event_participants
INSERT INTO tbl_event_participants (event_id, user_id, attendance_status) VALUES
(1, 1, 1),
(2, 2, 1),
(3, 3, 0),
(4, 3, 1),
(5, 5, 0);

-- Insert into tbl_event_feedback
INSERT INTO tbl_event_feedback (event_id, user_id, rating, comments) VALUES
(4, 3, 5, 'Excellent workshop, very informative and hands-on.'),
(1, 1, 4, 'Well organized, but the internet was a bit slow.'),
(2, 2, 5, 'The speaker was amazing! Very inspiring talk.'),
(4, 1, 3, 'Could have been better if the duration was longer.');

-- Insert into tbl_resources
INSERT INTO tbl_resources (name, type, quantity, description, is_available, maintenance_status) VALUES
('Projector Screen', 'AV Equipment', 10, 'Portable 100-inch projector screens', 1, 'Available'),
('Microphone Set', 'AV Equipment', 20, 'Wireless microphone with stand', 1, 'Available'),
('Tables', 'Furniture', 100, '6-foot rectangular tables', 1, 'Available'),
('Chairs', 'Furniture', 500, 'Standard plastic chairs', 0, 'Under Maintenance'),
('Sound System', 'AV Equipment', 5, 'High-power speakers with mixer', 1, 'Available');

-- Insert into tbl_event_resources
INSERT INTO tbl_event_resources (event_id, resource_id, quantity_booked, booking_start, booking_end) VALUES
(1, 2, 5, '2025-10-20 08:00:00', '2025-10-20 18:00:00'),
(1, 3, 50, '2025-10-20 08:00:00', '2025-10-20 18:00:00'),
(2, 1, 1, '2025-11-05 10:00:00', '2025-11-05 14:00:00'),
(3, 5, 2, '2025-12-15 09:00:00', '2025-12-15 23:00:00'),
(4, 3, 25, '2025-10-25 09:00:00', '2025-10-25 17:00:00');

-- Insert into tbl_resource_maintenance
INSERT INTO tbl_resource_maintenance (resource_id, maintenance_start, maintenance_end, description, performed_by) VALUES
(4, '2025-09-01 09:00:00', '2025-09-15 17:00:00', 'Repairing broken legs and cleaning all chairs', 'Campus Maintenance Team'),
(1, '2025-08-20 10:00:00', '2025-08-20 12:00:00', 'Routine check and cleaning', 'AV Support'),
(5, '2025-07-10 14:00:00', '2025-07-10 16:00:00', 'Firmware update on the audio mixer', 'AV Support');
