CREATE DATABASE IF NOT EXISTS redrat_proxy;
USE redrat_proxy;

CREATE TABLE IF NOT EXISTS remotes (
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

CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    is_admin BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sessions (
    session_id VARCHAR(255) PRIMARY KEY,
    user_id INT NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS remote_files (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    filename VARCHAR(255) NOT NULL,
    filepath VARCHAR(255) NOT NULL,
    device_type VARCHAR(255),
    uploaded_by INT NOT NULL,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (uploaded_by) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS commands (
    id INT AUTO_INCREMENT PRIMARY KEY,
    remote_id INT NOT NULL,
    command VARCHAR(255) NOT NULL,
    device VARCHAR(255),
    ir_port INT DEFAULT 1,
    power INT DEFAULT 100,
    status ENUM('pending', 'executed', 'failed') NOT NULL DEFAULT 'pending',
    created_by INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    executed_at TIMESTAMP NULL,
    status_updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (remote_id) REFERENCES remotes(id) ON DELETE CASCADE,
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS sequences (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    created_by INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS sequence_commands (
    id INT AUTO_INCREMENT PRIMARY KEY,
    sequence_id INT NOT NULL,
    command VARCHAR(255) NOT NULL,
    device VARCHAR(255),
    remote_id INT NOT NULL,
    ir_port INT DEFAULT 1,
    power INT DEFAULT 100,
    position INT NOT NULL,
    delay_ms INT NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (sequence_id) REFERENCES sequences(id) ON DELETE CASCADE,
    FOREIGN KEY (remote_id) REFERENCES remotes(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS schedules (
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

CREATE TABLE IF NOT EXISTS command_templates (
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

-- RedRat devices table
CREATE TABLE IF NOT EXISTS redrat_devices (
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

-- API keys table
CREATE TABLE IF NOT EXISTS api_keys (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    key_hash VARCHAR(64) NOT NULL,
    user_id INT NOT NULL,
    expires_at TIMESTAMP NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE KEY unique_key_hash (key_hash),
    INDEX idx_user_id (user_id),
    INDEX idx_key_hash (key_hash)
);

-- Default admin user (password: admin)
-- This hash is generated using bcrypt with 12 rounds
INSERT INTO users (username, password_hash, is_admin)
VALUES ('admin', '$2b$12$8NwSjJj4cdXkS76kNakZy.y0Fih5.jB/0KjBh94AVsCxpgIMnX9/S', TRUE);