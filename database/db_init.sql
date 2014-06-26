--Initialize the tables:

CREATE DATABASE `centinel_schema` /*!40100 DEFAULT CHARACTER SET utf32 */;

CREATE TABLE `clients` (
  `client_tag` varchar(45) NOT NULL,
  `public_key` longtext NOT NULL,
  `last_online` datetime DEFAULT NULL,
  `last_ip_port` varchar(45) DEFAULT NULL,
  `authorized` int(11) NOT NULL,
  `full_name` varchar(45) DEFAULT NULL,
  `email` varchar(45) DEFAULT NULL,
  `country` int(11) DEFAULT NULL,
  PRIMARY KEY (`client_tag`),
  UNIQUE KEY `client_tag_UNIQUE` (`client_tag`)
) ENGINE=InnoDB DEFAULT CHARSET=utf32;

CREATE TABLE `client_groups` (
  `client_tag` varchar(45) DEFAULT NULL,
  `group_tag` varchar(45) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf32;

