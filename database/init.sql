-- Cria o DB (se não existir) e seleciona
CREATE DATABASE IF NOT EXISTS app_db
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE app_db;

-- ===== TABLE users =====
CREATE TABLE IF NOT EXISTS users (
  id            INT AUTO_INCREMENT PRIMARY KEY,
  email         VARCHAR(255) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  name          VARCHAR(100) NOT NULL,
  created_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_unicode_ci;

-- ===== TABLE tasks =====
CREATE TABLE IF NOT EXISTS tasks (
  id         INT AUTO_INCREMENT PRIMARY KEY,
  owner_id   INT NOT NULL,
  title      VARCHAR(200) NOT NULL,
  description TEXT NULL,
  start_at   DATETIME NOT NULL,
  end_at     DATETIME NOT NULL,
  status     ENUM('todo','doing','done') NOT NULL DEFAULT 'todo',
  priority   ENUM('low','medium','high') NOT NULL DEFAULT 'medium',
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

  CONSTRAINT fk_tasks_owner
    FOREIGN KEY (owner_id) REFERENCES users(id)
    ON DELETE CASCADE,

  INDEX idx_tasks_owner (owner_id),
  INDEX idx_tasks_time (start_at, end_at),
  INDEX idx_tasks_status (status),
  INDEX idx_tasks_priority (priority)
) ENGINE=InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_unicode_ci;
