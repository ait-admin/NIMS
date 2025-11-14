CREATE DATABASE IF NOT EXISTS hospital_kiosk;
USE hospital_kiosk;
DROP TABLE IF EXISTS appointments;

DROP TABLE IF EXISTS patients;

CREATE TABLE patients (
    cr_number VARCHAR(20) PRIMARY KEY,
    name VARCHAR(100),
    age INT,
    gender VARCHAR(10),
    doctor VARCHAR(100),
    department VARCHAR(100),
    last_visit DATE
);

CREATE TABLE appointments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    cr_number VARCHAR(20),
    doctor VARCHAR(100),
    appointment_time DATETIME,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (cr_number) REFERENCES patients(cr_number)
);

INSERT INTO patients (cr_number, name, age, gender, doctor, department, last_visit) VALUES
('CR1001', 'Ramesh Kumar', 45, 'Male', 'Dr. Mehta', 'Cardiology', '2025-09-20'),
('CR1002', 'Lakshmi Devi', 52, 'Female', 'Dr. Patel', 'Endocrinology', '2025-09-22'),
('CR1003', 'Rajesh Singh', 39, 'Male', 'Dr. Sharma', 'ENT', '2025-09-25');



