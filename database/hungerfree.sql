-- =====================================================================
--  HungerFree - Food Donation System
--  COMPLETE database script: Donor + Receiver (NGO) + Admin
--  Works on MySQL 5.7 / 8.x and MariaDB 10.x
--
--  HOW TO RUN
--    MySQL Workbench : File > Open SQL Script > pick this file >
--                      click the lightning-bolt icon (runs everything)
--    phpMyAdmin      : open the "Import" tab and choose this file
--    Command line    : mysql -u root -p < hungerfree.sql
--
--  WARNING: this script DELETES and re-creates these 7 tables:
--      donor, ngos, donation, pickup_request, admin, feedback, notification
--  Any rows already in them are lost. Other tables are not touched.
--
--  TABLE OVERVIEW
--    donor        restaurants / hotels / caterers          (DN001...)
--    ngos         NGOs, orphanages, old age homes          (RN001...)
--    donation     food posted by donors, accepted by NGOs
--    pickup_request  record of which NGO accepted / collected a donation
--    admin        administrator accounts                   (AD001...)
--    feedback     ratings / comments from donors and NGOs
--    notification messages the admin sends to users
--
--  No table is needed for "Manage Users" or "Reports": those admin
--  pages are built with queries over donor, ngos and donation.
-- =====================================================================

CREATE DATABASE IF NOT EXISTS `hungerfree`
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_general_ci;

USE `hungerfree`;

SET FOREIGN_KEY_CHECKS = 0;

DROP TABLE IF EXISTS `pickup_request`;
DROP TABLE IF EXISTS `donation`;
DROP TABLE IF EXISTS `donor`;
DROP TABLE IF EXISTS `ngos`;
DROP TABLE IF EXISTS `admin`;
DROP TABLE IF EXISTS `feedback`;
DROP TABLE IF EXISTS `notification`;

SET FOREIGN_KEY_CHECKS = 1;


-- ---------------------------------------------------------------------
--  DONOR
--  `resturaent_name` keeps the spelling used in app.py.
--  `password` holds a ~118 character hash: keep it VARCHAR(255).
--  `confirm_password` is no longer used for real data (stored as '').
--  `status` is for the admin "Manage Donors" page (Active / Inactive).
-- ---------------------------------------------------------------------
CREATE TABLE `donor` (
  `donor_id`         VARCHAR(10)   NOT NULL,
  `resturaent_name`  VARCHAR(255)  NOT NULL,
  `owner_name`       VARCHAR(255)  NOT NULL,
  `email`            VARCHAR(190)  NOT NULL,
  `phone`            VARCHAR(30)   NOT NULL,
  `address`          TEXT          NOT NULL,
  `city`             VARCHAR(100)  NOT NULL,
  `password`         VARCHAR(255)  NOT NULL,
  `confirm_password` VARCHAR(255)  NOT NULL DEFAULT '',
  `location`         TEXT          NOT NULL,
  `status`           VARCHAR(20)   NOT NULL DEFAULT 'Active',
  `created_at`       TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`donor_id`),
  UNIQUE KEY `uq_donor_email` (`email`),
  KEY `idx_donor_city` (`city`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;


-- ---------------------------------------------------------------------
--  NGOS  (receivers)
--  `status` is for the admin "Manage NGOs" page (Active / Inactive).
-- ---------------------------------------------------------------------
CREATE TABLE `ngos` (
  `ngo_id`              VARCHAR(10)   NOT NULL,
  `organization_name`   VARCHAR(255)  NOT NULL,
  `organization_type`   VARCHAR(100)  NOT NULL,
  `representative_name` VARCHAR(255)  NOT NULL,
  `email`               VARCHAR(190)  NOT NULL,
  `phone`               VARCHAR(30)   NOT NULL,
  `address`             TEXT          NOT NULL,
  `city`                VARCHAR(100)  NOT NULL,
  `password`            VARCHAR(255)  NOT NULL,
  `confirm_password`    VARCHAR(255)  NOT NULL DEFAULT '',
  `location`            TEXT          NOT NULL,
  `status`              VARCHAR(20)   NOT NULL DEFAULT 'Active',
  `created_at`          TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`ngo_id`),
  UNIQUE KEY `uq_ngos_email` (`email`),
  KEY `idx_ngos_city` (`city`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;


-- ---------------------------------------------------------------------
--  DONATION
--  status      : 'Pending' when posted. The pages use these words:
--                Pending, Accepted / Approved, Picked Up, Rejected.
--                Pick ONE spelling for each when you build the
--                receiver and admin backend (the column accepts any).
--  food_image  : the browser sends the photo as base64 text -> LONGTEXT.
--  ngo_id      : the NGO that accepted it (NULL until accepted).
--  pickup_time : app.py inserts NULL, so it must allow NULL.
-- ---------------------------------------------------------------------
CREATE TABLE `donation` (
  `donation_id`    INT           NOT NULL AUTO_INCREMENT,
  `donor_id`       VARCHAR(10)   NOT NULL,
  `food_name`      VARCHAR(255)  NOT NULL,
  `food_category`  VARCHAR(50)   NOT NULL,
  `quantity`       VARCHAR(100)  NOT NULL,
  `cooking_date`   DATE          NOT NULL,
  `expiry_time`    TIME          NOT NULL,
  `contact_number` VARCHAR(30)   NOT NULL DEFAULT '',
  `description`    TEXT          NULL,
  `food_image`     LONGTEXT      NULL,
  `pickup_time`    DATETIME      NULL,
  `status`         VARCHAR(20)   NOT NULL DEFAULT 'Pending',
  `ngo_id`         VARCHAR(10)   NULL,
  `accepted_at`    DATETIME      NULL,
  `created_at`     TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`donation_id`),
  KEY `idx_donation_donor`  (`donor_id`),
  KEY `idx_donation_status` (`status`),
  KEY `idx_donation_ngo`    (`ngo_id`),
  CONSTRAINT `fk_donation_donor`
    FOREIGN KEY (`donor_id`) REFERENCES `donor` (`donor_id`)
    ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `fk_donation_ngo`
    FOREIGN KEY (`ngo_id`) REFERENCES `ngos` (`ngo_id`)
    ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;


-- ---------------------------------------------------------------------
--  PICKUP_REQUEST  (transaction history for the receiver side:
--                   Accept -> Picked Up / Collected)
--  UNIQUE(donation_id) = one donation can be accepted by only ONE NGO,
--  so two organizations can never claim the same food. If an NGO
--  cancels, delete its row so the food becomes available again.
--  Keep donation.status and donation.ngo_id in step with this table.
-- ---------------------------------------------------------------------
CREATE TABLE `pickup_request` (
  `request_id`   INT           NOT NULL AUTO_INCREMENT,
  `donation_id`  INT           NOT NULL,
  `ngo_id`       VARCHAR(10)   NOT NULL,
  `status`       VARCHAR(20)   NOT NULL DEFAULT 'Accepted',
  `pickup_time`  DATETIME      NULL,
  `collected_at` DATETIME      NULL,
  `notes`        TEXT          NULL,
  `created_at`   TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`request_id`),
  UNIQUE KEY `uq_pickup_donation` (`donation_id`),
  KEY `idx_pickup_ngo`    (`ngo_id`),
  KEY `idx_pickup_status` (`status`),
  CONSTRAINT `fk_pickup_donation`
    FOREIGN KEY (`donation_id`) REFERENCES `donation` (`donation_id`)
    ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `fk_pickup_ngo`
    FOREIGN KEY (`ngo_id`) REFERENCES `ngos` (`ngo_id`)
    ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;


-- ---------------------------------------------------------------------
--  ADMIN  (admin profile page: ID, username, email, role,
--          joining date, last login)
--  `password` must store a hash, never the plain password.
-- ---------------------------------------------------------------------
CREATE TABLE `admin` (
  `admin_id`   VARCHAR(10)   NOT NULL,
  `username`   VARCHAR(100)  NOT NULL,
  `email`      VARCHAR(190)  NOT NULL,
  `password`   VARCHAR(255)  NOT NULL,
  `role`       VARCHAR(30)   NOT NULL DEFAULT 'Admin',
  `last_login` DATETIME      NULL,
  `created_at` TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`admin_id`),
  UNIQUE KEY `uq_admin_username` (`username`),
  UNIQUE KEY `uq_admin_email` (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;


-- ---------------------------------------------------------------------
--  FEEDBACK  (admin Feedback page: ID, user name, role, rating,
--             feedback text, date)
--  `user_id` is a DN... or RN... id, so it has no foreign key
--  (it points at either donor or ngos depending on `role`).
-- ---------------------------------------------------------------------
CREATE TABLE `feedback` (
  `feedback_id` INT           NOT NULL AUTO_INCREMENT,
  `user_id`     VARCHAR(10)   NOT NULL,
  `user_name`   VARCHAR(255)  NOT NULL,
  `role`        VARCHAR(20)   NOT NULL,
  `rating`      TINYINT       NOT NULL DEFAULT 5,
  `message`     TEXT          NOT NULL,
  `created_at`  TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`feedback_id`),
  KEY `idx_feedback_role` (`role`),
  KEY `idx_feedback_user` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;


-- ---------------------------------------------------------------------
--  NOTIFICATION  (admin Notifications page: ID, title, sent to,
--                 date, status)
--  sent_to : 'All Users', 'Food Donors' or 'NGOs'
-- ---------------------------------------------------------------------
CREATE TABLE `notification` (
  `notification_id` INT           NOT NULL AUTO_INCREMENT,
  `title`           VARCHAR(255)  NOT NULL,
  `message`         TEXT          NOT NULL,
  `sent_to`         VARCHAR(30)   NOT NULL,
  `status`          VARCHAR(20)   NOT NULL DEFAULT 'Sent',
  `created_at`      TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`notification_id`),
  KEY `idx_notification_sent_to` (`sent_to`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
