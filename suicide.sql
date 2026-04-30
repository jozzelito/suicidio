CREATE DATABASE suicide_rate;
USE suicide_rate;

--  ## TABLA 1: ENTIDAD
--  Catálogo de entidades federativas y nivel nacional --

CREATE TABLE entity (
    cve_entity   TINYINT UNSIGNED NOT NULL PRIMARY KEY,
    name        VARCHAR(60)      NOT NULL,
    is_national   BOOLEAN          NOT NULL DEFAULT FALSE COMMENT 'TRUE = agregado nacional'
);

-- ## TABLA 2: YEAR 
-- # Catálogo de años del período de estudio --
CREATE TABLE YEAR (
    year   SMALLINT NOT NULL PRIMARY KEY
);

-- ##  TABLA 3: POBLACION
#  Población por entidad, año y sexo (base para cálculo de tasas) --
CREATE TABLE poblation (
    id_poblation INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    year SMALLINT NOT NULL,
    cve_entity TINYINT UNSIGNED NOT NULL,
    pop_men INT UNSIGNED NOT NULL,
    pop_women INT UNSIGNED NOT NULL,
    pop_total INT UNSIGNED NOT NULL,
    FOREIGN KEY (year) REFERENCES year(year),
    FOREIGN KEY (cve_entity) REFERENCES entity(cve_entity)
);

--  ## TABLA 4: SUICIDIO
--  Casos y tasas de suicidio por entidad, año y sexo --
CREATE TABLE suicidio (
    id_suicidio INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    year SMALLINT NOT NULL,
    cve_entity TINYINT UNSIGNED NOT NULL,
    hombres SMALLINT UNSIGNED NOT NULL DEFAULT 0,
    mujeres SMALLINT UNSIGNED NOT NULL DEFAULT 0,
    desconocido SMALLINT UNSIGNED NOT NULL DEFAULT 0,
    total SMALLINT UNSIGNED NOT NULL DEFAULT 0,
    tasa_hombres DECIMAL(10,6) COMMENT 'Por 100,000 habitantes hombres',
    tasa_mujeres DECIMAL(10,6) COMMENT 'Por 100,000 habitantes mujeres',
    tasa_total DECIMAL(10,6) COMMENT 'Por 100,000 habitantes totales',
    FOREIGN KEY (year) REFERENCES year(year),
    FOREIGN KEY (cve_entity) REFERENCES entity(cve_entity)
);

INSERT INTO entity (cve_entity, name, is_national) VALUES
(0,  'Nacional', TRUE),
(1,  'Aguascalientes', FALSE),
(2,  'Baja California', FALSE),
(3,  'Baja California Sur', FALSE),
(4,  'Campeche', FALSE),
(5,  'Coahuila', FALSE),
(6,  'Colima', FALSE),
(7,  'Chiapas', FALSE),
(8,  'Chihuahua', FALSE),
(9,  'Ciudad de Mexico', FALSE),
(10, 'Durango', FALSE),
(11, 'Guanajuato', FALSE),
(12, 'Guerrero', FALSE),
(13, 'Hidalgo', FALSE),
(14, 'Jalisco', FALSE),
(15, 'Estado de Mexico', FALSE),
(16, 'Michoacan', FALSE),
(17, 'Morelos', FALSE),
(18, 'Nayarit', FALSE),
(19, 'Nuevo Leon', FALSE),
(20, 'Oaxaca', FALSE),
(21, 'Puebla', FALSE),
(22, 'Queretaro', FALSE),
(23, 'Quintana Roo', FALSE),
(24, 'San Luis Potosi', FALSE),
(25, 'Sinaloa', FALSE),
(26, 'Sonora', FALSE),
(27, 'Tabasco', FALSE),
(28, 'Tamaulipas', FALSE),
(29, 'Tlaxcala', FALSE),
(30, 'Veracruz', FALSE),
(31, 'Yucatan', FALSE),
(32, 'Zacatecas', FALSE);