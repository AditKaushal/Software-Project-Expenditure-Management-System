CREATE DATABASE IF NOT EXISTS `tracker`;
USE `tracker`;

CREATE TABLE IF NOT EXISTS `users` (
    `id` INT NOT NULL AUTO_INCREMENT,
    `first_name` VARCHAR(100) DEFAULT NULL,
    `last_name` VARCHAR(100) DEFAULT NULL,
    `email` VARCHAR(100) DEFAULT NULL,
    `username` VARCHAR(100) DEFAULT NULL,
    `password` VARCHAR(100) DEFAULT NULL,
    `role` VARCHAR(100) DEFAULT 'user',
    PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `transactions` (
    `id` INT NOT NULL AUTO_INCREMENT,
    `user_id` INT,
    `amount` INT NOT NULL DEFAULT '0',
    `description` VARCHAR(255) DEFAULT NULL,
    `category` VARCHAR(255) DEFAULT NULL,
`date` TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY user_id (`user_id`),
    CONSTRAINT transactions_ibfk_1 FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
