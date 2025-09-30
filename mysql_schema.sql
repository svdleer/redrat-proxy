-- RedRat Proxy Database Schema
-- Clean schema with only admin user data
-- Database: redrat_proxy

CREATE DATABASE IF NOT EXISTS redrat_proxy;
USE redrat_proxy;

-- Remotes table - stores remote control definitions
CREATE TABLE remotes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    manufacturer VARCHAR(255),
    device_model_number VARCHAR(255),
    remote_model_number VARCHAR(255),
    device_type VARCHAR(255),
    decoder_class VARCHAR(255),
    description TEXT,
    image_path VARCHAR(255),
    config_data JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Users table - application users
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    is_admin BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Sessions table - user authentication sessions
CREATE TABLE sessions (
    session_id VARCHAR(255) PRIMARY KEY,
    user_id INT NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Remote files table - uploaded remote control files
CREATE TABLE remote_files (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    filename VARCHAR(255) NOT NULL,
    filepath VARCHAR(255) NOT NULL,
    device_type VARCHAR(255),
    uploaded_by INT NOT NULL,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (uploaded_by) REFERENCES users(id) ON DELETE CASCADE
);

-- Commands table - individual IR commands
CREATE TABLE commands (
    id INT AUTO_INCREMENT PRIMARY KEY,
    remote_id INT NOT NULL,
    command VARCHAR(255) NOT NULL,
    device VARCHAR(255),
    ir_port INT DEFAULT 1,
    power INT DEFAULT 50,
    status ENUM('pending', 'executed', 'failed') NOT NULL DEFAULT 'pending',
    created_by INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    executed_at TIMESTAMP NULL,
    status_updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (remote_id) REFERENCES remotes(id) ON DELETE CASCADE,
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE CASCADE
);

-- Sequences table - command sequences/macros
CREATE TABLE sequences (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    commands JSON NOT NULL,
    device VARCHAR(255),
    ir_port INT DEFAULT 1,
    power INT DEFAULT 50,
    status ENUM('pending', 'executing', 'completed', 'failed') NOT NULL DEFAULT 'pending',
    created_by INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    executed_at TIMESTAMP NULL,
    status_updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE CASCADE
);

-- Sequence commands table - individual commands within sequences
CREATE TABLE sequence_commands (
    id INT AUTO_INCREMENT PRIMARY KEY,
    sequence_id INT NOT NULL,
    command VARCHAR(255) NOT NULL,
    device VARCHAR(255),
    remote_id INT NOT NULL,
    ir_port INT DEFAULT 1,
    power INT DEFAULT 50,
    position INT NOT NULL,
    delay_ms INT NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (sequence_id) REFERENCES sequences(id) ON DELETE CASCADE,
    FOREIGN KEY (remote_id) REFERENCES remotes(id) ON DELETE CASCADE
);

-- Schedules table - scheduled commands and sequences
CREATE TABLE schedules (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    type ENUM('command', 'sequence') NOT NULL,
    target_id INT NOT NULL,
    schedule_type ENUM('once', 'daily', 'weekly', 'monthly') NOT NULL,
    schedule_data JSON NOT NULL,
    next_run DATETIME NOT NULL,
    last_run DATETIME NULL,
    status ENUM('pending', 'active', 'paused', 'completed') NOT NULL DEFAULT 'active',
    created_by INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE CASCADE
);

-- Scheduled tasks table - for SchedulingService daemon
CREATE TABLE scheduled_tasks (
    id VARCHAR(36) PRIMARY KEY,
    type ENUM('command', 'sequence') NOT NULL,
    target_id VARCHAR(255) NOT NULL,
    schedule_type ENUM('once', 'daily', 'weekly', 'monthly') NOT NULL,
    schedule_data JSON NOT NULL,
    next_run DATETIME NOT NULL,
    last_run DATETIME NULL,
    status ENUM('pending', 'active', 'paused', 'completed') NOT NULL DEFAULT 'active',
    created_by INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE CASCADE
);

-- Command templates table - parsed command templates from remote files
CREATE TABLE command_templates (
    id INT AUTO_INCREMENT PRIMARY KEY,
    file_id INT NOT NULL,
    name VARCHAR(255) NOT NULL,
    device_type VARCHAR(255),
    template_data JSON NOT NULL,
    created_by INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (file_id) REFERENCES remote_files(id) ON DELETE CASCADE,
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE CASCADE
);

-- RedRat devices table - physical RedRat IR devices
CREATE TABLE redrat_devices (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    ip_address VARCHAR(45) NOT NULL,
    port INT NOT NULL DEFAULT 10001,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    last_status_check TIMESTAMP NULL,
    last_status ENUM('online', 'offline', 'error') DEFAULT 'offline',
    device_model INT NULL,
    device_ports INT NULL,
    port_descriptions JSON NULL,
    created_by INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE KEY unique_device (ip_address, port)
);

-- API keys table - API authentication keys
CREATE TABLE api_keys (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    key_hash VARCHAR(64) NOT NULL,
    user_id INT NOT NULL,
    expires_at TIMESTAMP NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_used_at TIMESTAMP NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE KEY unique_key_hash (key_hash),
    INDEX idx_user_id (user_id),
    INDEX idx_key_hash (key_hash),
    INDEX idx_last_used_at (last_used_at)
);

-- Insert default admin user
-- Username: admin
-- Password: admin
-- Password hash generated using bcrypt with 12 rounds
INSERT INTO users (username, password_hash, is_admin) VALUES 
('admin', '$2b$12$lVwTWPNZg1iPpKtcjWFHPujK3Cvi6rwWG1kw7p.DHkGg4P9WlKNa2', TRUE);

-- Insert default API key
-- API Key: rr_X_Tk5fZC3h8_oUln1IZeGQT07-5QxqJrKLeLdy5uTwE
-- Hash generated using SHA-256
INSERT INTO api_keys (name, key_hash, user_id, is_active) VALUES 
('Default API Key', '2e8822c3b2c57a177ed65a47f22c7a67e5e7b4ce104db2aea5578e74bb54a9f7', 1, TRUE);

-- Create indexes for better performance
CREATE INDEX idx_commands_status ON commands(status);
CREATE INDEX idx_commands_created_at ON commands(created_at);
CREATE INDEX idx_sequences_status ON sequences(status);
CREATE INDEX idx_remotes_name ON remotes(name);
CREATE INDEX idx_remote_files_uploaded_by ON remote_files(uploaded_by);
CREATE INDEX idx_sessions_expires_at ON sessions(expires_at);
CREATE INDEX idx_redrat_devices_status ON redrat_devices(last_status);
CREATE INDEX idx_schedules_next_run ON schedules(next_run);
CREATE INDEX idx_schedules_status ON schedules(status);

-- Set default charset and collation
ALTER DATABASE redrat_proxy CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
