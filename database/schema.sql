SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0;
SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0;
SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='TRADITIONAL,ALLOW_INVALID_DATES';

CREATE SCHEMA IF NOT EXISTS `mydb` DEFAULT CHARACTER SET utf8 COLLATE utf8_general_ci ;
USE `mydb` ;

-- -----------------------------------------------------
-- Table `mydb`.`countries`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `mydb`.`countries` (
  `id` INT(11) NOT NULL,
  `name` VARCHAR(45) NULL,
  PRIMARY KEY (`id`),
  UNIQUE INDEX `id_UNIQUE` (`id` ASC))
ENGINE = InnoDB
COMMENT = 'Static country list.';


-- -----------------------------------------------------
-- Table `mydb`.`users`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `mydb`.`users` (
  `email` TEXT NOT NULL,
  `name` TEXT NULL,
  `country` INT(11) NULL,
  `passwd` VARCHAR(45) NULL,
  PRIMARY KEY (`email`),
  UNIQUE INDEX `email_UNIQUE` (`email` ASC),
  INDEX `country_idx` (`country` ASC),
  CONSTRAINT `country`
    FOREIGN KEY (`country`)
    REFERENCES `mydb`.`countries` (`id`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION)
ENGINE = InnoDB
COMMENT = 'Users who have completed the registration form, will have a  /* comment truncated */ /*record on this table.*/';


-- -----------------------------------------------------
-- Table `mydb`.`clients`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `mydb`.`clients` (
  `tag` TEXT NOT NULL,
  `owner_email` TEXT NULL,
  `authorized` INT NULL,
  `public_key` LONGTEXT NULL,
  PRIMARY KEY (`tag`),
  UNIQUE INDEX `tag_UNIQUE` (`tag` ASC),
  INDEX `user_idx` (`owner_email` ASC),
  CONSTRAINT `user`
    FOREIGN KEY (`owner_email`)
    REFERENCES `mydb`.`users` (`email`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION)
ENGINE = InnoDB
DEFAULT CHARACTER SET = utf32
COMMENT = 'Client instance information including tag, owner, and autori /* comment truncated */ /*zation status.*/';


-- -----------------------------------------------------
-- Table `mydb`.`client_locations`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `mydb`.`client_locations` (
  `tag` TEXT NULL,
  `location` TEXT NULL,
  `timestamp` DATETIME NULL,
  INDEX `tag_idx` (`tag` ASC),
  CONSTRAINT `tag`
    FOREIGN KEY (`tag`)
    REFERENCES `mydb`.`clients` (`tag`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION)
ENGINE = InnoDB
COMMENT = 'IP addresses from which a client connected to the server and /* comment truncated */ /* times when it was online from those addresses.*/';


SET SQL_MODE=@OLD_SQL_MODE;
SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS;
SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS;
