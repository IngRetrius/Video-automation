-- MySQL Script for Reddit Stories Automation System
SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0;
SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0;
SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='ONLY_FULL_GROUP_BY,STRICT_TRANS_TABLES,NO_ZERO_IN_DATE,NO_ZERO_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION';

-- -----------------------------------------------------
-- Schema reddit_stories_automation
-- -----------------------------------------------------
CREATE SCHEMA IF NOT EXISTS `reddit_stories_automation` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE `reddit_stories_automation`;

-- -----------------------------------------------------
-- Table `reddit_stories_automation`.`reddit_stories`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `reddit_stories_automation`.`reddit_stories` (
  `id` BIGINT(20) NOT NULL AUTO_INCREMENT,
  `reddit_id` VARCHAR(50) NOT NULL UNIQUE,
  `title` VARCHAR(512) NOT NULL,
  `content` TEXT NOT NULL,
  `author` VARCHAR(128) NULL,
  `score` INT NULL DEFAULT 0,
  `upvote_ratio` FLOAT NULL,
  `num_comments` INT NULL DEFAULT 0,
  `post_flair` VARCHAR(50) NULL,
  `is_nsfw` BOOLEAN DEFAULT FALSE,
  `awards_received` INT NULL DEFAULT 0,
  `url` VARCHAR(512) NOT NULL,
  `created_utc` TIMESTAMP NULL,
  `collected_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `language` ENUM('es', 'en') NOT NULL DEFAULT 'es',
  `status` ENUM('pending', 'processing', 'processed', 'failed', 'published') DEFAULT 'pending',
  `importance_score` INT NULL DEFAULT 0,
  PRIMARY KEY (`id`),
  INDEX `idx_reddit_id` (`reddit_id` ASC),
  INDEX `idx_status` (`status` ASC),
  INDEX `idx_date` (`created_utc` ASC)
) ENGINE = InnoDB DEFAULT CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci;

-- -----------------------------------------------------
-- Table `reddit_stories_automation`.`processed_content`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `reddit_stories_automation`.`processed_content` (
  `id` BIGINT(20) NOT NULL AUTO_INCREMENT,
  `story_id` BIGINT(20) NOT NULL,
  `cleaned_content` TEXT NULL,
  `tts_script` TEXT NULL,
  `audio_path` VARCHAR(255) NULL,
  `background_video_path` VARCHAR(255) NULL,
  `final_video_path` VARCHAR(255) NULL,
  `duration_seconds` INT NULL,
  `processing_date` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  INDEX `story_id_idx` (`story_id` ASC),
  CONSTRAINT `fk_story_processed`
    FOREIGN KEY (`story_id`)
    REFERENCES `reddit_stories_automation`.`reddit_stories` (`id`)
    ON DELETE CASCADE
) ENGINE = InnoDB DEFAULT CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci;

-- -----------------------------------------------------
-- Table `reddit_stories_automation`.`youtube_publications`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `reddit_stories_automation`.`youtube_publications` (
  `id` BIGINT(20) NOT NULL AUTO_INCREMENT,
  `processed_content_id` BIGINT(20) NOT NULL,
  `youtube_video_id` VARCHAR(50) NULL,
  `youtube_url` VARCHAR(255) NULL,
  `youtube_title` VARCHAR(255) NULL,
  `youtube_description` TEXT NULL,
  `youtube_tags` TEXT NULL,
  `scheduled_time` DATETIME NOT NULL,
  `publication_status` ENUM('scheduled', 'published', 'failed') DEFAULT 'scheduled',
  `published_at` TIMESTAMP NULL,
  `views_count` INT NULL DEFAULT 0,
  `likes_count` INT NULL DEFAULT 0,
  PRIMARY KEY (`id`),
  INDEX `processed_content_id_idx` (`processed_content_id` ASC),
  CONSTRAINT `fk_processed_publication`
    FOREIGN KEY (`processed_content_id`)
    REFERENCES `reddit_stories_automation`.`processed_content` (`id`)
    ON DELETE CASCADE
) ENGINE = InnoDB DEFAULT CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci;

-- -----------------------------------------------------
-- Table `reddit_stories_automation`.`error_logs`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `reddit_stories_automation`.`error_logs` (
  `id` BIGINT(20) NOT NULL AUTO_INCREMENT,
  `related_table` VARCHAR(50) NULL,
  `related_id` BIGINT(20) NULL,
  `error_type` VARCHAR(50) NULL,
  `error_message` TEXT NULL,
  `error_timestamp` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `resolved` BOOLEAN DEFAULT FALSE,
  PRIMARY KEY (`id`),
  INDEX `idx_timestamp` (`error_timestamp` ASC)
) ENGINE = InnoDB DEFAULT CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci;

-- -----------------------------------------------------
-- Table `reddit_stories_automation`.`system_config`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `reddit_stories_automation`.`system_config` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `config_key` VARCHAR(50) NOT NULL UNIQUE,
  `config_value` TEXT NULL,
  `description` TEXT NULL,
  `last_updated` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE = InnoDB DEFAULT CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci;

-- -----------------------------------------------------
-- View `reddit_stories_automation`.`vw_stories_status`
-- -----------------------------------------------------
CREATE OR REPLACE VIEW `reddit_stories_automation`.`vw_stories_status` AS
SELECT 
    rs.id AS story_id,
    rs.reddit_id,
    rs.title,
    rs.author,
    rs.score,
    rs.status,
    rs.created_utc,
    pc.cleaned_content,
    pc.audio_path,
    pc.final_video_path,
    yp.youtube_url,
    yp.publication_status,
    yp.views_count,
    yp.likes_count
FROM reddit_stories rs
LEFT JOIN processed_content pc ON rs.id = pc.story_id
LEFT JOIN youtube_publications yp ON pc.id = yp.processed_content_id;

-- -----------------------------------------------------
-- View `reddit_stories_automation`.`vw_pending_publications`
-- -----------------------------------------------------
CREATE OR REPLACE VIEW `reddit_stories_automation`.`vw_pending_publications` AS
SELECT 
    rs.title,
    rs.author,
    rs.score,
    pc.processing_date,
    yp.scheduled_time,
    yp.youtube_title,
    yp.publication_status
FROM youtube_publications yp
JOIN processed_content pc ON yp.processed_content_id = pc.id
JOIN reddit_stories rs ON pc.story_id = rs.id
WHERE yp.publication_status = 'scheduled'
ORDER BY yp.scheduled_time;

-- -----------------------------------------------------
-- View `reddit_stories_automation`.`vw_processing_monitor`
-- -----------------------------------------------------
CREATE OR REPLACE VIEW `reddit_stories_automation`.`vw_processing_monitor` AS
SELECT 
    rs.id AS story_id,
    rs.title,
    rs.collected_at,
    rs.status AS story_status,
    pc.processing_date,
    CASE 
        WHEN pc.id IS NULL THEN 'Pending Processing'
        WHEN yp.id IS NULL THEN 'Pending Publication'
        ELSE yp.publication_status
    END AS current_status
FROM reddit_stories rs
LEFT JOIN processed_content pc ON rs.id = pc.story_id
LEFT JOIN youtube_publications yp ON pc.id = yp.processed_content_id
ORDER BY rs.collected_at DESC;

-- -----------------------------------------------------
-- Trigger `update_story_status_after_processing`
-- -----------------------------------------------------
DELIMITER $$
CREATE TRIGGER update_story_status_after_processing
AFTER INSERT ON processed_content
FOR EACH ROW
BEGIN
    UPDATE reddit_stories 
    SET status = 'processed' 
    WHERE id = NEW.story_id;
END$$

-- -----------------------------------------------------
-- Trigger `log_youtube_publication_changes`
-- -----------------------------------------------------
CREATE TRIGGER log_youtube_publication_changes
AFTER UPDATE ON youtube_publications
FOR EACH ROW
BEGIN
    IF OLD.publication_status != NEW.publication_status THEN
        INSERT INTO error_logs (
            related_table,
            related_id,
            error_type,
            error_message,
            resolved
        ) VALUES (
            'youtube_publications',
            NEW.id,
            'status_change',
            CONCAT('Status changed from ', OLD.publication_status, ' to ', NEW.publication_status),
            TRUE
        );
    END IF;
END$$

DELIMITER ;

SET SQL_MODE=@OLD_SQL_MODE;
SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS;
SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS;

-- Insert initial system configuration
INSERT INTO system_config (config_key, config_value, description) VALUES
('last_scrape_time', NULL, 'Timestamp of the last successful Reddit scrape'),
('min_score_threshold', '50', 'Minimum score (upvotes) required for processing'),
('max_story_length', '5000', 'Maximum character length for stories to process'),
('youtube_upload_hour', '14', 'Hour of the day to schedule YouTube uploads (24h format)'),
('tts_language', 'es-ES', 'Default language for text-to-speech conversion');
select * from reddit_stories;
select * from processed_content;
ALTER TABLE `reddit_stories_automation`.`processed_content`
ADD COLUMN IF NOT EXISTS `status` ENUM('pending', 'processing', 'processed', 'published', 'failed') 
DEFAULT 'pending' AFTER `processing_date`,
ADD INDEX `idx_content_status` (`status`);
CREATE TABLE IF NOT EXISTS `reddit_stories_automation`.`tiktok_publications` (
  `id` BIGINT(20) NOT NULL AUTO_INCREMENT,
  `processed_content_id` BIGINT(20) NOT NULL,
  `tiktok_video_id` VARCHAR(50) UNIQUE,
  `tiktok_url` VARCHAR(255),
  `scheduled_time` DATETIME,
  `published_at` TIMESTAMP NULL,
  `status` ENUM('pending', 'scheduled', 'published', 'failed') DEFAULT 'pending',
  `views_count` INT DEFAULT 0,
  `likes_count` INT DEFAULT 0,
  `shares_count` INT DEFAULT 0,
  `comments_count` INT DEFAULT 0,
  `error_message` TEXT,
  `extra_data` JSON,
  PRIMARY KEY (`id`),
  INDEX `idx_tiktok_status` (`status`),
  INDEX `idx_tiktok_published` (`published_at`),
  CONSTRAINT `fk_tiktok_processed_content` 
    FOREIGN KEY (`processed_content_id`) 
    REFERENCES `processed_content` (`id`) 
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE OR REPLACE VIEW `vw_content_stats` AS
SELECT 
    rs.title,
    rs.author,
    rs.importance_score,
    pc.status as content_status,
    pc.processing_date,
    COALESCE(tp.status, 'not_uploaded') as tiktok_status,
    tp.views_count as tiktok_views,
    tp.likes_count as tiktok_likes,
    tp.shares_count as tiktok_shares,
    tp.comments_count as tiktok_comments,
    COALESCE(yp.publication_status, 'not_uploaded') as youtube_status,
    yp.views_count as youtube_views,
    yp.likes_count as youtube_likes
FROM reddit_stories rs
LEFT JOIN processed_content pc ON rs.id = pc.story_id
LEFT JOIN tiktok_publications tp ON pc.id = tp.processed_content_id
LEFT JOIN youtube_publications yp ON pc.id = yp.processed_content_id
WHERE rs.status != 'pending'
ORDER BY pc.processing_date DESC;
CREATE OR REPLACE VIEW `vw_pending_publications` AS
SELECT 
    rs.id as story_id,
    rs.title,
    rs.importance_score,
    pc.id as content_id,
    pc.status as content_status,
    pc.processing_date,
    COALESCE(tp.status, 'not_uploaded') as tiktok_status,
    COALESCE(yp.publication_status, 'not_uploaded') as youtube_status
FROM reddit_stories rs
JOIN processed_content pc ON rs.id = pc.story_id
LEFT JOIN tiktok_publications tp ON pc.id = tp.processed_content_id
LEFT JOIN youtube_publications yp ON pc.id = yp.processed_content_id
WHERE 
    pc.status = 'processed' 
    AND (tp.id IS NULL OR yp.id IS NULL)
ORDER BY rs.importance_score DESC;
