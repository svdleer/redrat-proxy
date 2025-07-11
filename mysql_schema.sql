CREATE DATABASE IF NOT EXISTS redrat_proxy;
USE redrat_proxy;

CREATE TABLE IF NOT EXISTS remotes (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    api_key VARCHAR(255) UNIQUE NOT NULL,
    image_path VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(36) PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    is_admin BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sessions (
    session_id VARCHAR(255) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS irdb_files (
    id VARCHAR(36) PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    filepath VARCHAR(255) NOT NULL,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS commands (
    id VARCHAR(36) PRIMARY KEY,
    remote_id VARCHAR(36) NOT NULL,
    name VARCHAR(255) NOT NULL,
    command_data TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (remote_id) REFERENCES remotes(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS command_sequences (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    created_by VARCHAR(36) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS sequence_commands (
    id VARCHAR(36) PRIMARY KEY,
    sequence_id VARCHAR(36) NOT NULL,
    command_id VARCHAR(36) NOT NULL,
    position INT NOT NULL,
    delay_ms INT NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (sequence_id) REFERENCES command_sequences(id) ON DELETE CASCADE,
    FOREIGN KEY (command_id) REFERENCES commands(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS scheduled_tasks (
    id VARCHAR(36) PRIMARY KEY,
    type ENUM('command', 'sequence') NOT NULL,
    target_id VARCHAR(36) NOT NULL,
    schedule_type ENUM('once', 'daily', 'weekly', 'monthly') NOT NULL,
    schedule_data JSON NOT NULL,
    next_run DATETIME NOT NULL,
    created_by VARCHAR(36) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS command_templates (
    id VARCHAR(36) PRIMARY KEY,
    irdb_id VARCHAR(36) NOT NULL,
    name VARCHAR(255) NOT NULL,
    template_data JSON NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (irdb_id) REFERENCES irdb_files(id) ON DELETE CASCADE
);

-- Default admin user (password: admin123)
-- This hash is generated using bcrypt with 12 rounds
INSERT INTO users (id, username, password_hash, is_admin)
VALUES ('admin-id', 'admin', '$2b$12$8NwSjJj4cdXkS76kNakZy.y0Fih5.jB/0KjBh94AVsCxpgIMnX9/S', TRUE);