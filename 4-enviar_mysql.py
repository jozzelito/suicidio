import pandas as pd
from mysql.connector import connect, Error
import os
import re
from contextlib import closing

print("=" * 60)
print("CARGANDO DATOS A MySQL - SUICIDE_RATE (Nuevo esquema)")
print("=" * 60)


# -- RUTAS ABSOLUTAS
BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
CSV_SUICIDIO  = os.path.join(BASE_DIR, 'datos_suicidio_limpios.csv')
CSV_DESEMPLEO = os.path.join(BASE_DIR, 'BdA', 'desempleo_completo_mexico.csv')

# -- VERIFICAR ARCHIVOS CSV
if not os.path.exists(CSV_SUICIDIO):
    print(f"ERROR: No encontrado: {CSV_SUICIDIO}")
    exit()

if not os.path.exists(CSV_DESEMPLEO):
    print(f"ERROR: No encontrado: {CSV_DESEMPLEO}")
    exit()

# -- DDL: TABLAS
TABLAS_DDL = {
    "entity": """
        CREATE TABLE entity (
            cve_entity  TINYINT UNSIGNED NOT NULL PRIMARY KEY,
            ent_name    VARCHAR(60)      NOT NULL,
            is_national BOOLEAN          NOT NULL DEFAULT FALSE
                        COMMENT 'TRUE = agregado nacional',
            INDEX idx_ent_name (ent_name)
        )
    """,
    "year_date": """
        CREATE TABLE year_date (
            year_date SMALLINT NOT NULL PRIMARY KEY
        )
    """,
    "population": """
        CREATE TABLE population (
            id_population INT UNSIGNED     NOT NULL AUTO_INCREMENT PRIMARY KEY,
            year_date     SMALLINT         NOT NULL,
            cve_entity    TINYINT UNSIGNED NOT NULL,
            pop_men       INT UNSIGNED     NOT NULL,
            pop_women     INT UNSIGNED     NOT NULL,
            pop_total     INT UNSIGNED     NOT NULL,
            FOREIGN KEY (year_date)  REFERENCES year_date(year_date),
            FOREIGN KEY (cve_entity) REFERENCES entity(cve_entity)
        )
    """,
    "suicide": """
        CREATE TABLE suicide (
            suicide_id     INT UNSIGNED      NOT NULL AUTO_INCREMENT PRIMARY KEY,
            year_date      SMALLINT          NOT NULL,
            cve_entity     TINYINT UNSIGNED  NOT NULL,
            male           SMALLINT UNSIGNED NOT NULL DEFAULT 0,
            female         SMALLINT UNSIGNED NOT NULL DEFAULT 0,
            unknown_gender SMALLINT UNSIGNED NOT NULL DEFAULT 0,
            total          SMALLINT UNSIGNED NOT NULL DEFAULT 0,
            rate_male      DECIMAL(10,6) COMMENT 'Por 100,000 habitantes hombres',
            rate_female    DECIMAL(10,6) COMMENT 'Por 100,000 habitantes mujeres',
            rate_total     DECIMAL(10,6) COMMENT 'Por 100,000 habitantes totales',
            FOREIGN KEY (year_date)  REFERENCES year_date(year_date),
            FOREIGN KEY (cve_entity) REFERENCES entity(cve_entity)
        )
    """,
    "unemployment": """
        CREATE TABLE unemployment (
            unemployment_id SMALLINT UNSIGNED NOT NULL AUTO_INCREMENT,
            year_date       SMALLINT          NOT NULL,
            cve_entity      TINYINT UNSIGNED  NOT NULL DEFAULT 0,
            rate_total      DECIMAL(5,3),
            rate_male       DECIMAL(5,3),
            rate_female     DECIMAL(5,3),
            PRIMARY KEY (unemployment_id),
            UNIQUE KEY uq_unemp (year_date, cve_entity),
            CONSTRAINT fk_unemp_year   FOREIGN KEY (year_date)  REFERENCES year_date(year_date),
            CONSTRAINT fk_unemp_entity FOREIGN KEY (cve_entity) REFERENCES entity(cve_entity)
        )
    """,
    "audit_log": """
        CREATE TABLE audit_log (
            log_id        BIGINT UNSIGNED  NOT NULL AUTO_INCREMENT,
            log_timestamp DATETIME(3)      NOT NULL DEFAULT CURRENT_TIMESTAMP(3)
                          COMMENT 'Marca de tiempo con precision de milisegundos',
            db_user       VARCHAR(100)     NOT NULL DEFAULT (CURRENT_USER())
                          COMMENT 'Usuario MySQL que ejecuto la operacion',
            table_name    VARCHAR(64)      NOT NULL COMMENT 'Tabla afectada',
            operation     ENUM('INSERT','UPDATE','DELETE') NOT NULL,
            record_id     VARCHAR(40)      NOT NULL COMMENT 'PK del registro afectado (como texto)',
            old_values    JSON                      COMMENT 'Estado anterior - NULL en INSERT',
            new_values    JSON                      COMMENT 'Estado nuevo   - NULL en DELETE',
            PRIMARY KEY (log_id),
            INDEX idx_audit_table     (table_name),
            INDEX idx_audit_operation (operation),
            INDEX idx_audit_ts        (log_timestamp),
            INDEX idx_audit_user      (db_user)
        )
    """
}

# -- DDL: STORED PROCEDURES
STORED_PROCEDURES = [
    # 1. sp_insert_entity
    """
    CREATE PROCEDURE sp_insert_entity(
        IN p_cve_entity  TINYINT UNSIGNED,
        IN p_ent_name    VARCHAR(60),
        IN p_is_national BOOLEAN
    )
    BEGIN
        DECLARE EXIT HANDLER FOR SQLEXCEPTION BEGIN ROLLBACK; RESIGNAL; END;
        START TRANSACTION;
            INSERT INTO entity (cve_entity, ent_name, is_national)
            VALUES (p_cve_entity, p_ent_name, p_is_national);
        COMMIT;
    END
    """,
    # 2. sp_update_entity
    """
    CREATE PROCEDURE sp_update_entity(
        IN p_cve_entity  TINYINT UNSIGNED,
        IN p_ent_name    VARCHAR(60),
        IN p_is_national BOOLEAN
    )
    BEGIN
        DECLARE EXIT HANDLER FOR SQLEXCEPTION BEGIN ROLLBACK; RESIGNAL; END;
        START TRANSACTION;
            UPDATE entity
               SET ent_name    = p_ent_name,
                   is_national = p_is_national
             WHERE cve_entity  = p_cve_entity;
            IF ROW_COUNT() = 0 THEN
                SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Entidad no encontrada.';
            END IF;
        COMMIT;
    END
    """,
    # 3. sp_insert_year
    """
    CREATE PROCEDURE sp_insert_year(
        IN p_year_date SMALLINT
    )
    BEGIN
        DECLARE EXIT HANDLER FOR SQLEXCEPTION BEGIN ROLLBACK; RESIGNAL; END;
        START TRANSACTION;
            INSERT INTO year_date (year_date) VALUES (p_year_date);
        COMMIT;
    END
    """,
    # 4. sp_upsert_population
    """
    CREATE PROCEDURE sp_upsert_population(
        IN p_year_date   SMALLINT,
        IN p_cve_entity  TINYINT UNSIGNED,
        IN p_pop_men     INT UNSIGNED,
        IN p_pop_women   INT UNSIGNED,
        IN p_pop_total   INT UNSIGNED
    )
    BEGIN
        DECLARE EXIT HANDLER FOR SQLEXCEPTION BEGIN ROLLBACK; RESIGNAL; END;
        START TRANSACTION;
            INSERT INTO population (year_date, cve_entity, pop_men, pop_women, pop_total)
            VALUES (p_year_date, p_cve_entity, p_pop_men, p_pop_women, p_pop_total)
            ON DUPLICATE KEY UPDATE
                pop_men   = VALUES(pop_men),
                pop_women = VALUES(pop_women),
                pop_total = VALUES(pop_total);
        COMMIT;
    END
    """,
    # 5. sp_upsert_suicide
    """
    CREATE PROCEDURE sp_upsert_suicide(
        IN p_year_date    SMALLINT,
        IN p_cve_entity   TINYINT UNSIGNED,
        IN p_male         SMALLINT UNSIGNED,
        IN p_female       SMALLINT UNSIGNED,
        IN p_unknown      SMALLINT UNSIGNED,
        IN p_total        SMALLINT UNSIGNED,
        IN p_rate_male    DECIMAL(10,6),
        IN p_rate_female  DECIMAL(10,6),
        IN p_rate_total   DECIMAL(10,6)
    )
    BEGIN
        DECLARE v_total SMALLINT UNSIGNED;
        DECLARE EXIT HANDLER FOR SQLEXCEPTION BEGIN ROLLBACK; RESIGNAL; END;
        SET v_total = IFNULL(p_total, p_male + p_female + p_unknown);
        START TRANSACTION;
            INSERT INTO suicide
                (year_date, cve_entity, male, female, unknown_gender, total,
                 rate_male, rate_female, rate_total)
            VALUES
                (p_year_date, p_cve_entity, p_male, p_female, p_unknown, v_total,
                 p_rate_male, p_rate_female, p_rate_total)
            ON DUPLICATE KEY UPDATE
                male           = VALUES(male),
                female         = VALUES(female),
                unknown_gender = VALUES(unknown_gender),
                total          = VALUES(total),
                rate_male      = VALUES(rate_male),
                rate_female    = VALUES(rate_female),
                rate_total     = VALUES(rate_total);
        COMMIT;
    END
    """,
    # 6. sp_upsert_unemployment
    """
    CREATE PROCEDURE sp_upsert_unemployment(
        IN p_year_date   SMALLINT,
        IN p_cve_entity  TINYINT UNSIGNED,
        IN p_rate_total  DECIMAL(5,3),
        IN p_rate_male   DECIMAL(5,3),
        IN p_rate_female DECIMAL(5,3)
    )
    BEGIN
        DECLARE EXIT HANDLER FOR SQLEXCEPTION BEGIN ROLLBACK; RESIGNAL; END;
        START TRANSACTION;
            INSERT INTO unemployment (year_date, cve_entity, rate_total, rate_male, rate_female)
            VALUES (p_year_date, p_cve_entity, p_rate_total, p_rate_male, p_rate_female)
            ON DUPLICATE KEY UPDATE
                rate_total  = VALUES(rate_total),
                rate_male   = VALUES(rate_male),
                rate_female = VALUES(rate_female);
        COMMIT;
    END
    """,
    # 7. sp_recalculate_suicide_rates
    """
    CREATE PROCEDURE sp_recalculate_suicide_rates(
        IN p_year_date   SMALLINT,
        IN p_cve_entity  TINYINT UNSIGNED
    )
    BEGIN
        DECLARE v_pop_men   INT UNSIGNED DEFAULT 0;
        DECLARE v_pop_women INT UNSIGNED DEFAULT 0;
        DECLARE v_pop_total INT UNSIGNED DEFAULT 0;
        DECLARE EXIT HANDLER FOR SQLEXCEPTION BEGIN ROLLBACK; RESIGNAL; END;
        SELECT pop_men, pop_women, pop_total
          INTO v_pop_men, v_pop_women, v_pop_total
          FROM population
         WHERE year_date = p_year_date AND cve_entity = p_cve_entity
         LIMIT 1;
        IF v_pop_total = 0 THEN
            SIGNAL SQLSTATE '45000'
                SET MESSAGE_TEXT = 'Poblacion no encontrada o es cero para el anio/entidad indicados.';
        END IF;
        START TRANSACTION;
            UPDATE suicide
               SET rate_male   = IF(v_pop_men   > 0, male   / v_pop_men   * 100000, NULL),
                   rate_female = IF(v_pop_women > 0, female / v_pop_women * 100000, NULL),
                   rate_total  = IF(v_pop_total > 0, total  / v_pop_total * 100000, NULL)
             WHERE year_date = p_year_date AND cve_entity = p_cve_entity;
        COMMIT;
    END
    """,
    # 8. sp_get_entity_trend
    """
    CREATE PROCEDURE sp_get_entity_trend(
        IN p_cve_entity      TINYINT UNSIGNED,
        IN p_year_date_from  SMALLINT,
        IN p_year_date_to    SMALLINT
    )
    BEGIN
        SELECT
            s.year_date,
            e.ent_name                      AS entity_name,
            s.total                         AS suicides_total,
            s.male                          AS suicides_male,
            s.female                        AS suicides_female,
            ROUND(s.rate_total,  4)         AS rate_per_100k,
            ROUND(s.rate_male,   4)         AS rate_male_per_100k,
            ROUND(s.rate_female, 4)         AS rate_female_per_100k
        FROM suicide  s
        JOIN entity   e ON e.cve_entity = s.cve_entity
        WHERE s.cve_entity = p_cve_entity
          AND s.year_date BETWEEN IFNULL(p_year_date_from, 2010)
                              AND IFNULL(p_year_date_to,   2024)
        ORDER BY s.year_date;
    END
    """,
    # 9. sp_get_national_summary
    """
    CREATE PROCEDURE sp_get_national_summary(
        IN p_year_date_from  SMALLINT,
        IN p_year_date_to    SMALLINT
    )
    BEGIN
        SELECT
            s.year_date,
            s.total                                           AS suicides_total,
            ROUND(s.rate_total,  4)                           AS suicide_rate_per_100k,
            ROUND(s.rate_male,   4)                           AS suicide_rate_male,
            ROUND(s.rate_female, 4)                           AS suicide_rate_female,
            ROUND(s.rate_male / NULLIF(s.rate_female, 0), 2)  AS ratio_male_female,
            p.pop_total,
            u.rate_total                                      AS unemployment_pct,
            u.rate_male                                       AS unemployment_male_pct,
            u.rate_female                                     AS unemployment_female_pct
        FROM suicide       s
        JOIN population    p ON p.year_date = s.year_date AND p.cve_entity = 0
        LEFT JOIN unemployment u ON u.year_date = s.year_date AND u.cve_entity = 0
        WHERE s.cve_entity = 0
          AND s.year_date BETWEEN IFNULL(p_year_date_from, 1900)
                              AND IFNULL(p_year_date_to,   2100)
        ORDER BY s.year_date;
    END
    """,
    # 10. sp_get_top_entities_by_year
    """
    CREATE PROCEDURE sp_get_top_entities_by_year(
        IN p_year_date  SMALLINT,
        IN p_top_n      INT UNSIGNED
    )
    BEGIN
        SET p_top_n = IFNULL(p_top_n, 5);
        SELECT
            e.cve_entity,
            e.ent_name                      AS entity_name,
            s.total                         AS suicides_total,
            ROUND(s.rate_total,  4)         AS rate_per_100k,
            ROUND(s.rate_male,   4)         AS rate_male_per_100k,
            ROUND(s.rate_female, 4)         AS rate_female_per_100k
        FROM suicide  s
        JOIN entity   e ON e.cve_entity = s.cve_entity
        WHERE s.year_date    = p_year_date
          AND e.is_national  = FALSE
        ORDER BY s.rate_total DESC
        LIMIT p_top_n;
    END
    """,
    # 11. sp_get_gender_gap_analysis
    """
    CREATE PROCEDURE sp_get_gender_gap_analysis(
        IN p_year_date_from  SMALLINT,
        IN p_year_date_to    SMALLINT
    )
    BEGIN
        SELECT
            s.year_date,
            ROUND(s.rate_male,   4)                           AS suicide_rate_male,
            ROUND(s.rate_female, 4)                           AS suicide_rate_female,
            ROUND(s.rate_male - s.rate_female, 4)             AS suicide_gap,
            ROUND(s.rate_male / NULLIF(s.rate_female, 0), 2)  AS suicide_ratio,
            u.rate_male                                       AS unemployment_male_pct,
            u.rate_female                                     AS unemployment_female_pct,
            ROUND(u.rate_female - u.rate_male, 3)             AS unemployment_gap
        FROM suicide       s
        LEFT JOIN unemployment u ON u.year_date = s.year_date AND u.cve_entity = 0
        WHERE s.cve_entity = 0
          AND s.year_date BETWEEN IFNULL(p_year_date_from, 2010)
                              AND IFNULL(p_year_date_to,   2024)
        ORDER BY s.year_date;
    END
    """,
    # 12. sp_get_decade_summary
    """
    CREATE PROCEDURE sp_get_decade_summary()
    BEGIN
        SELECT
            CONCAT(FLOOR(s.year_date / 10) * 10, 's')  AS decade,
            COUNT(DISTINCT s.year_date)                 AS years_counted,
            SUM(s.total)                                AS total_suicides,
            ROUND(AVG(s.rate_total), 4)                 AS avg_suicide_rate,
            ROUND(MAX(s.rate_total), 4)                 AS max_suicide_rate,
            ROUND(MIN(s.rate_total), 4)                 AS min_suicide_rate,
            ROUND(AVG(u.rate_total), 3)                 AS avg_unemployment_pct
        FROM suicide       s
        LEFT JOIN unemployment u ON u.year_date = s.year_date AND u.cve_entity = 0
        WHERE s.cve_entity = 0
        GROUP BY decade
        ORDER BY decade;
    END
    """,
    # 13. sp_audit_log_purge
    """
    CREATE PROCEDURE sp_audit_log_purge(
        IN p_days_to_keep INT UNSIGNED
    )
    BEGIN
        DECLARE v_cutoff DATETIME(3);
        SET p_days_to_keep = IFNULL(p_days_to_keep, 90);
        SET v_cutoff = NOW(3) - INTERVAL p_days_to_keep DAY;
        DELETE FROM audit_log WHERE log_timestamp < v_cutoff;
        SELECT ROW_COUNT() AS rows_deleted, v_cutoff AS cutoff_date;
    END
    """,
    # 14. sp_audit_log_report
    """
    CREATE PROCEDURE sp_audit_log_report(
        IN p_table_name VARCHAR(64)
    )
    BEGIN
        SELECT
            table_name,
            operation,
            COUNT(*)                AS total_events,
            MIN(log_timestamp)      AS first_event,
            MAX(log_timestamp)      AS last_event,
            COUNT(DISTINCT db_user) AS distinct_users
        FROM audit_log
        WHERE (p_table_name IS NULL OR table_name = p_table_name)
        GROUP BY table_name, operation
        ORDER BY table_name, operation;
    END
    """,
    # 15. sp_delete_entity
    """
    CREATE PROCEDURE sp_delete_entity(
        IN p_cve_entity TINYINT UNSIGNED
    )
    BEGIN
        DECLARE v_count INT DEFAULT 0;
        DECLARE EXIT HANDLER FOR SQLEXCEPTION BEGIN ROLLBACK; RESIGNAL; END;
        SELECT COUNT(*) INTO v_count FROM population   WHERE cve_entity = p_cve_entity;
        IF v_count > 0 THEN
            SIGNAL SQLSTATE '45000'
                SET MESSAGE_TEXT = 'No se puede eliminar: la entidad tiene registros en population.';
        END IF;
        SELECT COUNT(*) INTO v_count FROM suicide      WHERE cve_entity = p_cve_entity;
        IF v_count > 0 THEN
            SIGNAL SQLSTATE '45000'
                SET MESSAGE_TEXT = 'No se puede eliminar: la entidad tiene registros en suicide.';
        END IF;
        SELECT COUNT(*) INTO v_count FROM unemployment WHERE cve_entity = p_cve_entity;
        IF v_count > 0 THEN
            SIGNAL SQLSTATE '45000'
                SET MESSAGE_TEXT = 'No se puede eliminar: la entidad tiene registros en unemployment.';
        END IF;
        START TRANSACTION;
            DELETE FROM entity WHERE cve_entity = p_cve_entity;
            IF ROW_COUNT() = 0 THEN
                SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Entidad no encontrada.';
            END IF;
        COMMIT;
    END
    """
]

# -- DDL: TRIGGERS
TRIGGERS = [
    # 1. entity AFTER INSERT
    """
    CREATE TRIGGER trg_entity_after_insert
    AFTER INSERT ON entity FOR EACH ROW
    BEGIN
        INSERT INTO audit_log (table_name, operation, record_id, new_values)
        VALUES ('entity', 'INSERT', NEW.cve_entity,
            JSON_OBJECT('cve_entity', NEW.cve_entity, 'ent_name', NEW.ent_name,
                        'is_national', NEW.is_national));
    END
    """,
    # 2. entity AFTER UPDATE
    """
    CREATE TRIGGER trg_entity_after_update
    AFTER UPDATE ON entity FOR EACH ROW
    BEGIN
        INSERT INTO audit_log (table_name, operation, record_id, old_values, new_values)
        VALUES ('entity', 'UPDATE', NEW.cve_entity,
            JSON_OBJECT('cve_entity', OLD.cve_entity, 'ent_name', OLD.ent_name,
                        'is_national', OLD.is_national),
            JSON_OBJECT('cve_entity', NEW.cve_entity, 'ent_name', NEW.ent_name,
                        'is_national', NEW.is_national));
    END
    """,
    # 3. entity AFTER DELETE
    """
    CREATE TRIGGER trg_entity_after_delete
    AFTER DELETE ON entity FOR EACH ROW
    BEGIN
        INSERT INTO audit_log (table_name, operation, record_id, old_values)
        VALUES ('entity', 'DELETE', OLD.cve_entity,
            JSON_OBJECT('cve_entity', OLD.cve_entity, 'ent_name', OLD.ent_name,
                        'is_national', OLD.is_national));
    END
    """,
    # 4. year_date AFTER INSERT
    """
    CREATE TRIGGER trg_year_after_insert
    AFTER INSERT ON year_date FOR EACH ROW
    BEGIN
        INSERT INTO audit_log (table_name, operation, record_id, new_values)
        VALUES ('year_date', 'INSERT', NEW.year_date,
            JSON_OBJECT('year_date', NEW.year_date));
    END
    """,
    # 5. year_date AFTER UPDATE
    """
    CREATE TRIGGER trg_year_after_update
    AFTER UPDATE ON year_date FOR EACH ROW
    BEGIN
        INSERT INTO audit_log (table_name, operation, record_id, old_values, new_values)
        VALUES ('year_date', 'UPDATE', NEW.year_date,
            JSON_OBJECT('year_date', OLD.year_date),
            JSON_OBJECT('year_date', NEW.year_date));
    END
    """,
    # 6. year_date AFTER DELETE
    """
    CREATE TRIGGER trg_year_after_delete
    AFTER DELETE ON year_date FOR EACH ROW
    BEGIN
        INSERT INTO audit_log (table_name, operation, record_id, old_values)
        VALUES ('year_date', 'DELETE', OLD.year_date,
            JSON_OBJECT('year_date', OLD.year_date));
    END
    """,
    # 7. population AFTER INSERT
    """
    CREATE TRIGGER trg_population_after_insert
    AFTER INSERT ON population FOR EACH ROW
    BEGIN
        INSERT INTO audit_log (table_name, operation, record_id, new_values)
        VALUES ('population', 'INSERT', NEW.id_population,
            JSON_OBJECT('id_population', NEW.id_population, 'year_date', NEW.year_date,
                        'cve_entity', NEW.cve_entity, 'pop_men', NEW.pop_men,
                        'pop_women', NEW.pop_women, 'pop_total', NEW.pop_total));
    END
    """,
    # 8. population AFTER UPDATE
    """
    CREATE TRIGGER trg_population_after_update
    AFTER UPDATE ON population FOR EACH ROW
    BEGIN
        INSERT INTO audit_log (table_name, operation, record_id, old_values, new_values)
        VALUES ('population', 'UPDATE', NEW.id_population,
            JSON_OBJECT('id_population', OLD.id_population, 'year_date', OLD.year_date,
                        'cve_entity', OLD.cve_entity, 'pop_men', OLD.pop_men,
                        'pop_women', OLD.pop_women, 'pop_total', OLD.pop_total),
            JSON_OBJECT('id_population', NEW.id_population, 'year_date', NEW.year_date,
                        'cve_entity', NEW.cve_entity, 'pop_men', NEW.pop_men,
                        'pop_women', NEW.pop_women, 'pop_total', NEW.pop_total));
    END
    """,
    # 9. population AFTER DELETE
    """
    CREATE TRIGGER trg_population_after_delete
    AFTER DELETE ON population FOR EACH ROW
    BEGIN
        INSERT INTO audit_log (table_name, operation, record_id, old_values)
        VALUES ('population', 'DELETE', OLD.id_population,
            JSON_OBJECT('id_population', OLD.id_population, 'year_date', OLD.year_date,
                        'cve_entity', OLD.cve_entity, 'pop_men', OLD.pop_men,
                        'pop_women', OLD.pop_women, 'pop_total', OLD.pop_total));
    END
    """,
    # 10. suicide AFTER INSERT
    """
    CREATE TRIGGER trg_suicide_after_insert
    AFTER INSERT ON suicide FOR EACH ROW
    BEGIN
        INSERT INTO audit_log (table_name, operation, record_id, new_values)
        VALUES ('suicide', 'INSERT', NEW.suicide_id,
            JSON_OBJECT('suicide_id', NEW.suicide_id, 'year_date', NEW.year_date,
                        'cve_entity', NEW.cve_entity, 'male', NEW.male,
                        'female', NEW.female, 'unknown_gender', NEW.unknown_gender,
                        'total', NEW.total, 'rate_male', NEW.rate_male,
                        'rate_female', NEW.rate_female, 'rate_total', NEW.rate_total));
    END
    """,
    # 11. suicide AFTER UPDATE
    """
    CREATE TRIGGER trg_suicide_after_update
    AFTER UPDATE ON suicide FOR EACH ROW
    BEGIN
        INSERT INTO audit_log (table_name, operation, record_id, old_values, new_values)
        VALUES ('suicide', 'UPDATE', NEW.suicide_id,
            JSON_OBJECT('suicide_id', OLD.suicide_id, 'year_date', OLD.year_date,
                        'cve_entity', OLD.cve_entity, 'male', OLD.male,
                        'female', OLD.female, 'unknown_gender', OLD.unknown_gender,
                        'total', OLD.total, 'rate_male', OLD.rate_male,
                        'rate_female', OLD.rate_female, 'rate_total', OLD.rate_total),
            JSON_OBJECT('suicide_id', NEW.suicide_id, 'year_date', NEW.year_date,
                        'cve_entity', NEW.cve_entity, 'male', NEW.male,
                        'female', NEW.female, 'unknown_gender', NEW.unknown_gender,
                        'total', NEW.total, 'rate_male', NEW.rate_male,
                        'rate_female', NEW.rate_female, 'rate_total', NEW.rate_total));
    END
    """,
    # 12. suicide AFTER DELETE
    """
    CREATE TRIGGER trg_suicide_after_delete
    AFTER DELETE ON suicide FOR EACH ROW
    BEGIN
        INSERT INTO audit_log (table_name, operation, record_id, old_values)
        VALUES ('suicide', 'DELETE', OLD.suicide_id,
            JSON_OBJECT('suicide_id', OLD.suicide_id, 'year_date', OLD.year_date,
                        'cve_entity', OLD.cve_entity, 'male', OLD.male,
                        'female', OLD.female, 'unknown_gender', OLD.unknown_gender,
                        'total', OLD.total, 'rate_male', OLD.rate_male,
                        'rate_female', OLD.rate_female, 'rate_total', OLD.rate_total));
    END
    """,
    # 13. unemployment AFTER INSERT
    """
    CREATE TRIGGER trg_unemployment_after_insert
    AFTER INSERT ON unemployment FOR EACH ROW
    BEGIN
        INSERT INTO audit_log (table_name, operation, record_id, new_values)
        VALUES ('unemployment', 'INSERT', NEW.unemployment_id,
            JSON_OBJECT('unemployment_id', NEW.unemployment_id, 'year_date', NEW.year_date,
                        'cve_entity', NEW.cve_entity, 'rate_total', NEW.rate_total,
                        'rate_male', NEW.rate_male, 'rate_female', NEW.rate_female));
    END
    """,
    # 14. unemployment AFTER UPDATE
    """
    CREATE TRIGGER trg_unemployment_after_update
    AFTER UPDATE ON unemployment FOR EACH ROW
    BEGIN
        INSERT INTO audit_log (table_name, operation, record_id, old_values, new_values)
        VALUES ('unemployment', 'UPDATE', NEW.unemployment_id,
            JSON_OBJECT('unemployment_id', OLD.unemployment_id, 'year_date', OLD.year_date,
                        'cve_entity', OLD.cve_entity, 'rate_total', OLD.rate_total,
                        'rate_male', OLD.rate_male, 'rate_female', OLD.rate_female),
            JSON_OBJECT('unemployment_id', NEW.unemployment_id, 'year_date', NEW.year_date,
                        'cve_entity', NEW.cve_entity, 'rate_total', NEW.rate_total,
                        'rate_male', NEW.rate_male, 'rate_female', NEW.rate_female));
    END
    """,
    # 15. unemployment AFTER DELETE
    """
    CREATE TRIGGER trg_unemployment_after_delete
    AFTER DELETE ON unemployment FOR EACH ROW
    BEGIN
        INSERT INTO audit_log (table_name, operation, record_id, old_values)
        VALUES ('unemployment', 'DELETE', OLD.unemployment_id,
            JSON_OBJECT('unemployment_id', OLD.unemployment_id, 'year_date', OLD.year_date,
                        'cve_entity', OLD.cve_entity, 'rate_total', OLD.rate_total,
                        'rate_male', OLD.rate_male, 'rate_female', OLD.rate_female));
    END
    """
]

# -- DDL: VISTAS
VISTAS = [
    """
    CREATE OR REPLACE VIEW vw_yearly_national_report AS
    SELECT s.year_date, s.male AS cases_male, s.female AS cases_female,
           s.unknown_gender AS cases_unknown_sex, s.total AS total_cases,
           ROUND(s.rate_male,   4) AS male_rate,
           ROUND(s.rate_female, 4) AS female_rate,
           ROUND(s.rate_total,  4) AS total_rate
    FROM suicide s
    JOIN entity  e ON e.cve_entity = s.cve_entity
    WHERE e.is_national = TRUE
    ORDER BY s.year_date
    """,
    """
    CREATE OR REPLACE VIEW vw_ranking_entity_average_rate AS
    SELECT e.ent_name AS entity, COUNT(s.year_date) AS year_by_dates,
           ROUND(AVG(s.rate_total),  4) AS total_average_rate,
           ROUND(AVG(s.rate_male),   4) AS total_average_rate_male,
           ROUND(AVG(s.rate_female), 4) AS total_average_rate_female,
           SUM(s.total) AS total_historic_cases
    FROM suicide s
    JOIN entity  e ON e.cve_entity = s.cve_entity
    WHERE e.is_national = FALSE
    GROUP BY e.cve_entity, e.ent_name
    ORDER BY total_average_rate DESC
    """,
    """
    CREATE OR REPLACE VIEW vw_time_series_entity AS
    SELECT e.ent_name AS entity, s.year_date,
           s.total AS total_cases, s.male AS male_cases, s.female AS female_cases,
           ROUND(s.rate_total,  4) AS total_rate,
           ROUND(s.rate_male,   4) AS male_rate,
           ROUND(s.rate_female, 4) AS female_rate
    FROM suicide s
    JOIN entity  e ON e.cve_entity = s.cve_entity
    WHERE e.is_national = FALSE
    ORDER BY e.ent_name, s.year_date
    """,
    """
    CREATE OR REPLACE VIEW vw_top5_entities_last_year AS
    SELECT e.ent_name AS entity, s.year_date,
           s.total AS total_cases,
           ROUND(s.rate_total,  4) AS total_rate,
           ROUND(s.rate_male,   4) AS male_rate,
           ROUND(s.rate_female, 4) AS female_rate
    FROM suicide s
    JOIN entity  e ON e.cve_entity = s.cve_entity
    WHERE e.is_national = FALSE
      AND s.year_date = (SELECT MAX(year_date) FROM suicide WHERE cve_entity != 0)
    ORDER BY s.rate_total DESC
    LIMIT 5
    """,
    """
    CREATE OR REPLACE VIEW vw_gender_entity_gap AS
    SELECT e.ent_name AS entity, s.year_date,
           ROUND(s.rate_male,   4) AS male_rate,
           ROUND(s.rate_female, 4) AS female_rate,
           ROUND(s.rate_male - s.rate_female, 4) AS real_gap,
           CASE WHEN s.rate_female > 0
                THEN ROUND(s.rate_male / s.rate_female, 2) ELSE NULL
           END AS male_female_ratio
    FROM suicide s
    JOIN entity  e ON e.cve_entity = s.cve_entity
    WHERE e.is_national = FALSE
      AND s.rate_male IS NOT NULL AND s.rate_female IS NOT NULL
    ORDER BY real_gap DESC
    """,
    """
    CREATE OR REPLACE VIEW vw_national_year_by_year_variation AS
    SELECT curr.year_date,
           ROUND(curr.rate_total, 4) AS total_rate,
           ROUND(prev.rate_total, 4) AS rate_past_year,
           ROUND(curr.rate_total - prev.rate_total, 4) AS absolute_change,
           CASE WHEN prev.rate_total > 0
                THEN ROUND(((curr.rate_total - prev.rate_total) / prev.rate_total) * 100, 2)
                ELSE NULL
           END AS porcentual_change
    FROM suicide curr
    JOIN suicide prev ON prev.cve_entity = curr.cve_entity
                      AND prev.year_date = curr.year_date - 1
    JOIN entity e ON e.cve_entity = curr.cve_entity
    WHERE e.is_national = TRUE
    ORDER BY curr.year_date
    """,
    """
    CREATE OR REPLACE VIEW vw_suicide_vs_unemployment AS
    SELECT e.ent_name AS entity, s.year_date,
           ROUND(s.rate_total,  4) AS suicide_rate,
           ROUND(s.rate_male,   4) AS male_suicide_rate,
           ROUND(s.rate_female, 4) AS female_suicide_rate,
           ROUND(u.rate_total,  3) AS unemployment_rate,
           ROUND(u.rate_male,   3) AS male_unemployment_rate,
           ROUND(u.rate_female, 3) AS female_unemployment_rate
    FROM suicide      s
    JOIN entity       e ON e.cve_entity = s.cve_entity
    JOIN unemployment u ON u.cve_entity = s.cve_entity AND u.year_date = s.year_date
    WHERE e.is_national = FALSE
    ORDER BY e.ent_name, s.year_date
    """,
    """
    CREATE OR REPLACE VIEW vw_historic_entity_growth AS
    WITH min_max_years AS (
        SELECT MIN(year_date) AS min_year, MAX(year_date) AS max_year
        FROM suicide WHERE cve_entity != 0
    )
    SELECT e.ent_name AS entity,
           s_ini.year_date AS start_year, ROUND(s_ini.rate_total, 4) AS start_rate,
           s_fin.year_date AS final_year, ROUND(s_fin.rate_total, 4) AS final_rate,
           ROUND(s_fin.rate_total - s_ini.rate_total, 4) AS absolute_change,
           CASE WHEN s_ini.rate_total > 0
                THEN ROUND(((s_fin.rate_total - s_ini.rate_total) / s_ini.rate_total) * 100, 2)
                ELSE NULL
           END AS percentage_change
    FROM entity e
    CROSS JOIN min_max_years mm
    JOIN suicide s_ini ON s_ini.cve_entity = e.cve_entity AND s_ini.year_date = mm.min_year
    JOIN suicide s_fin ON s_fin.cve_entity = e.cve_entity AND s_fin.year_date = mm.max_year
    WHERE e.is_national = FALSE
    ORDER BY absolute_change DESC
    """,
    """
    CREATE OR REPLACE VIEW vw_accomulated_entity_cases AS
    SELECT e.ent_name AS entity,
           SUM(s.male) AS total_male, SUM(s.female) AS total_female,
           SUM(s.unknown_gender) AS total_unknown, SUM(s.total) AS total_cases,
           MIN(s.year_date) AS start_year, MAX(s.year_date) AS last_year
    FROM suicide s
    JOIN entity  e ON e.cve_entity = s.cve_entity
    WHERE e.is_national = FALSE
    GROUP BY e.cve_entity, e.ent_name
    ORDER BY total_cases DESC
    """,
    """
    CREATE OR REPLACE VIEW vw_average_per_decade_national AS
    SELECT CONCAT(FLOOR(s.year_date / 10) * 10, 's') AS decade,
           COUNT(DISTINCT s.year_date) AS year_per_decade,
           ROUND(AVG(s.rate_total),  4) AS total_average_rate,
           ROUND(AVG(s.rate_male),   4) AS male_average_rate,
           ROUND(AVG(s.rate_female), 4) AS female_average_rate,
           SUM(s.total) AS cases_per_decade
    FROM suicide s
    JOIN entity  e ON e.cve_entity = s.cve_entity
    WHERE e.is_national = TRUE
    GROUP BY FLOOR(s.year_date / 10)
    ORDER BY decade
    """,
    """
    CREATE OR REPLACE VIEW vw_ranking_female_rate AS
    SELECT e.ent_name AS entity,
           ROUND(AVG(s.rate_female), 4) AS female_average_rate,
           ROUND(MIN(s.rate_female), 4) AS female_minimum_rate,
           ROUND(MAX(s.rate_female), 4) AS female_maximum_rate,
           SUM(s.female) AS total_female_cases
    FROM suicide s
    JOIN entity  e ON e.cve_entity = s.cve_entity
    WHERE e.is_national = FALSE AND s.rate_female IS NOT NULL
    GROUP BY e.cve_entity, e.ent_name
    ORDER BY female_average_rate DESC
    """,
    """
    CREATE OR REPLACE VIEW vw_ranking_male_rate AS
    SELECT e.ent_name AS entity,
           ROUND(AVG(s.rate_male), 4) AS male_average_rate,
           ROUND(MIN(s.rate_male), 4) AS male_minimum_rate,
           ROUND(MAX(s.rate_male), 4) AS male_maximum_rate,
           SUM(s.male) AS total_male_cases
    FROM suicide s
    JOIN entity  e ON e.cve_entity = s.cve_entity
    WHERE e.is_national = FALSE AND s.rate_male IS NOT NULL
    GROUP BY e.cve_entity, e.ent_name
    ORDER BY male_average_rate DESC
    """,
    """
    CREATE OR REPLACE VIEW vw_historic_peak_per_entity AS
    SELECT e.ent_name AS entity, s.year_date AS peak_year,
           s.total AS cases_in_peak,
           ROUND(s.rate_total,  4) AS total_peak_rate,
           ROUND(s.rate_male,   4) AS total_peak_male,
           ROUND(s.rate_female, 4) AS total_peak_female
    FROM suicide s
    JOIN entity  e ON e.cve_entity = s.cve_entity
    WHERE e.is_national = FALSE
      AND s.rate_total = (
            SELECT MAX(s2.rate_total) FROM suicide s2
            WHERE s2.cve_entity = s.cve_entity)
    ORDER BY total_peak_rate DESC
    """,
    """
    CREATE OR REPLACE VIEW vw_regional_ccomparative AS
    SELECT
        CASE
            WHEN e.cve_entity IN (2,3,26,8,5,19,28,10,25,32,18)       THEN 'Norte'
            WHEN e.cve_entity IN (14,6,1,11,22,16,15,9,13,29,17,21,24) THEN 'Centro'
            WHEN e.cve_entity IN (12,20,7,30,27,4,31,23)               THEN 'Sur'
        END AS region,
        e.ent_name AS entity,
        ROUND(AVG(s.rate_total),  4) AS total_average_rate,
        ROUND(AVG(s.rate_male),   4) AS male_average_rate,
        ROUND(AVG(s.rate_female), 4) AS female_average_rate,
        SUM(s.total) AS historic_cases
    FROM suicide s
    JOIN entity  e ON e.cve_entity = s.cve_entity
    WHERE e.is_national = FALSE
    GROUP BY region, e.cve_entity, e.ent_name
    ORDER BY region, total_average_rate DESC
    """,
    """
    CREATE OR REPLACE VIEW vw_case_density_per_population AS
    SELECT e.ent_name AS entity, s.year_date,
           p.pop_total, s.total AS total_cases,
           ROUND(s.rate_total, 4) AS rate_per_100k,
           CASE WHEN s.total > 0
                THEN ROUND(p.pop_total / s.total, 0) ELSE NULL
           END AS pop_per_case
    FROM suicide    s
    JOIN entity     e ON e.cve_entity = s.cve_entity
    JOIN population p ON p.cve_entity = s.cve_entity AND p.year_date = s.year_date
    WHERE e.is_national = FALSE
    ORDER BY e.ent_name, s.year_date
    """
]

ORDEN_TRUNCAR = ['suicide', 'population', 'unemployment', 'year_date', 'entity', 'audit_log']
ORDEN_CREAR   = ['entity', 'year_date', 'population', 'suicide', 'unemployment', 'audit_log']


def verificar_o_crear_tabla(cursor, tabla, ddl):
    cursor.execute("""
        SELECT COUNT(*) FROM information_schema.tables
        WHERE table_schema = 'suicide_rate' AND table_name = %s
    """, (tabla,))
    if cursor.fetchone()[0]:
        print(f"   OK  {tabla} ya existe")
        return False
    else:
        cursor.execute(ddl)
        print(f"   NEW {tabla} creada")
        return True


def procedure_existe(cursor, nombre):
    cursor.execute("""
        SELECT COUNT(*) FROM information_schema.routines
        WHERE routine_schema = 'suicide_rate'
          AND routine_type   = 'PROCEDURE'
          AND routine_name   = %s
    """, (nombre,))
    return cursor.fetchone()[0] > 0


def trigger_existe(cursor, nombre):
    cursor.execute("""
        SELECT COUNT(*) FROM information_schema.triggers
        WHERE trigger_schema = 'suicide_rate'
          AND trigger_name   = %s
    """, (nombre,))
    return cursor.fetchone()[0] > 0


try:
    with connect(
            host="127.0.0.1",
            user="root",
            password="Tocino",
            port=3306
    ) as conexion:

        with closing(conexion.cursor()) as cursor:
            print("Conectado a MySQL")

            # -- VERIFICAR / CREAR BASE DE DATOS
            print("\nVerificando base de datos 'suicide_rate'...")
            cursor.execute("""
                SELECT COUNT(*) FROM information_schema.schemata
                WHERE schema_name = 'suicide_rate'
            """)
            if cursor.fetchone()[0] == 0:
                cursor.execute(
                    "CREATE DATABASE suicide_rate "
                    "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
                )
                print("   NEW Base de datos 'suicide_rate' creada")
            else:
                print("   OK  Base de datos 'suicide_rate' encontrada")

            cursor.execute("USE suicide_rate")

            # -- VERIFICAR / CREAR TABLAS
            print("\nVerificando/creando tablas...")
            tablas_creadas = 0
            for tabla in ORDEN_CREAR:
                if verificar_o_crear_tabla(cursor, tabla, TABLAS_DDL[tabla]):
                    tablas_creadas += 1
            conexion.commit()
            print(f"   {tablas_creadas} tabla(s) nueva(s) creada(s)")

            # -- CREAR STORED PROCEDURES
            print("\nVerificando/creando Stored Procedures...")
            sp_creados = 0
            sp_omitidos = 0
            for ddl in STORED_PROCEDURES:
                match = re.search(r'CREATE PROCEDURE\s+(\w+)', ddl, re.IGNORECASE)
                nombre = match.group(1) if match else None
                if nombre:
                    if procedure_existe(cursor, nombre):
                        print(f"   OK  {nombre} ya existe")
                        sp_omitidos += 1
                    else:
                        cursor.execute(ddl)
                        print(f"   NEW {nombre} creado")
                        sp_creados += 1
            conexion.commit()
            print(f"   {sp_creados} SP(s) creado(s), {sp_omitidos} ya existian")

            # -- CREAR TRIGGERS
            print("\nVerificando/creando Triggers...")
            trg_creados = 0
            trg_omitidos = 0
            for ddl in TRIGGERS:
                match = re.search(r'CREATE TRIGGER\s+(\w+)', ddl, re.IGNORECASE)
                nombre = match.group(1) if match else None
                if nombre:
                    if trigger_existe(cursor, nombre):
                        print(f"   OK  {nombre} ya existe")
                        trg_omitidos += 1
                    else:
                        cursor.execute(ddl)
                        print(f"   NEW {nombre} creado")
                        trg_creados += 1
            conexion.commit()
            print(f"   {trg_creados} trigger(s) creado(s), {trg_omitidos} ya existian")

            # -- CREAR VISTAS
            print("\nCreando/actualizando Vistas...")
            for ddl in VISTAS:
                match = re.search(r'VIEW\s+(\w+)\s+AS', ddl, re.IGNORECASE)
                nombre = match.group(1) if match else '???'
                cursor.execute(ddl)
                print(f"   OK  {nombre} lista")
            conexion.commit()
            print(f"   {len(VISTAS)} vista(s) creadas/actualizadas")

            # -- CARGAR CSVs
            df_suicidio  = pd.read_csv(CSV_SUICIDIO)
            df_desempleo = pd.read_csv(CSV_DESEMPLEO)
            print(f"\nCSV suicidios  cargado : {len(df_suicidio)} filas")
            print(f"CSV desempleo  cargado : {len(df_desempleo)} filas")

            # -- VACIAR TABLAS
            print("\nVaciando tablas existentes...")
            cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
            for tabla in ORDEN_TRUNCAR:
                cursor.execute("""
                    SELECT COUNT(*) FROM information_schema.tables
                    WHERE table_schema = 'suicide_rate' AND table_name = %s
                """, (tabla,))
                if cursor.fetchone()[0]:
                    cursor.execute(f"TRUNCATE TABLE {tabla}")
                    print(f"   OK  {tabla} vaciada")
                else:
                    print(f"   SKIP {tabla} no existe, se omite")
            cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
            print("   Proceso de limpieza completado")

            # -- INSERTAR: ENTITY
            print("\nInsertando ENTITY...")
            entities = df_suicidio[['cve_ent', 'ent_name']].drop_duplicates()
            sql_entity = """
                INSERT INTO entity (cve_entity, ent_name, is_national)
                VALUES (%s, %s, %s)
            """
            for _, row in entities.iterrows():
                is_national = 1 if row['cve_ent'] == 0 else 0
                cursor.execute(sql_entity, (int(row['cve_ent']), row['ent_name'], is_national))
            conexion.commit()
            print(f"   {len(entities)} entidades insertadas")

            # -- INSERTAR: YEAR_DATE
            print("\nInsertando YEAR_DATE...")
            years = sorted(set(df_suicidio['year_date'].unique()) |
                           set(df_desempleo['year_date'].unique()))
            for year in years:
                cursor.execute("INSERT INTO year_date (year_date) VALUES (%s)", (int(year),))
            conexion.commit()
            print(f"   {len(years)} anyos insertados")

            # -- INSERTAR: POPULATION
            print("\nInsertando POPULATION...")
            pop_data = df_suicidio[
                ['year_date', 'cve_ent', 'male_pop', 'female_pop', 'poblation']
            ].drop_duplicates()
            sql_population = """
                INSERT INTO population (year_date, cve_entity, pop_men, pop_women, pop_total)
                VALUES (%s, %s, %s, %s, %s)
            """
            count_pop = 0
            for _, row in pop_data.iterrows():
                cursor.execute(sql_population, (
                    int(row['year_date']), int(row['cve_ent']),
                    int(row['male_pop']), int(row['female_pop']), int(row['poblation'])
                ))
                count_pop += 1
            conexion.commit()
            print(f"   {count_pop} registros de poblacion insertados")

            # -- INSERTAR: SUICIDE
            print("\nInsertando SUICIDE...")
            sql_suicide = """
                INSERT INTO suicide (
                    year_date, cve_entity, male, female, unknown_gender,
                    total, rate_male, rate_female, rate_total
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            count_suicide = 0
            for _, row in df_suicidio.iterrows():
                cursor.execute(sql_suicide, (
                    int(row['year_date']), int(row['cve_ent']),
                    int(row['male_suicides']), int(row['women_suicides']),
                    int(row['unknown_gender']), int(row['total_suicides']),
                    float(row['male_rate'])    if pd.notna(row['male_rate'])    else 0,
                    float(row['female_rate'])  if pd.notna(row['female_rate'])  else 0,
                    float(row['suicide_rate']) if pd.notna(row['suicide_rate']) else 0
                ))
                count_suicide += 1
            conexion.commit()
            print(f"   {count_suicide} registros de suicidios insertados")

            # -- INSERTAR: UNEMPLOYMENT
            print("\nInsertando UNEMPLOYMENT (datos reales)...")
            sql_unemployment = """
                INSERT INTO unemployment (year_date, cve_entity, rate_total, rate_male, rate_female)
                VALUES (%s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    rate_total  = VALUES(rate_total),
                    rate_male   = VALUES(rate_male),
                    rate_female = VALUES(rate_female)
            """
            count_unemp = 0
            for _, row in df_desempleo.iterrows():
                rate_male   = float(row['rate_male'])   if pd.notna(row['rate_male'])   else None
                rate_female = float(row['rate_female']) if pd.notna(row['rate_female']) else None
                rate_total  = float(row['rate_total'])  if pd.notna(row['rate_total'])  else None
                cursor.execute(sql_unemployment, (
                    int(row['year_date']), 0, rate_total, rate_male, rate_female
                ))
                count_unemp += 1
            conexion.commit()
            print(f"   {count_unemp} registros de desempleo insertados")
            print("   Datos nacionales reales (2010-2024)")
            print("   NOTA: Anyos 2010-2016 sin desglose por sexo (NULL en rate_male/rate_female)")

            # -- VERIFICACION FINAL
            print("\n" + "=" * 60)
            print("VERIFICACION DE DATOS INSERTADOS")
            print("=" * 60)

            for tabla in ['entity', 'year_date', 'population', 'suicide', 'unemployment']:
                cursor.execute(f"SELECT COUNT(*) FROM {tabla}")
                print(f"  {tabla:14} : {cursor.fetchone()[0]:>8,} registros")

            print("\nMUESTRA - Suicidios nacionales 2023:")
            cursor.execute("""
                SELECT s.year_date, e.ent_name, s.total, s.rate_total
                FROM suicide s
                JOIN entity e ON s.cve_entity = e.cve_entity
                WHERE s.year_date = 2023 AND s.cve_entity = 0
            """)
            resultado = cursor.fetchone()
            if resultado:
                print(f"  Anio            : {resultado[0]}")
                print(f"  Entidad         : {resultado[1]}")
                print(f"  Total suicidios : {resultado[2]:,}")
                print(f"  Tasa (x100,000) : {resultado[3]:.2f}")

            print("\nMUESTRA - Desempleo nacional 2023:")
            cursor.execute("""
                SELECT u.year_date, e.ent_name, u.rate_total, u.rate_male, u.rate_female
                FROM unemployment u
                JOIN entity e ON u.cve_entity = e.cve_entity
                WHERE u.year_date = 2023 AND u.cve_entity = 0
            """)
            resultado = cursor.fetchone()
            if resultado:
                print(f"  Anio            : {resultado[0]}")
                print(f"  Entidad         : {resultado[1]}")
                print(f"  Tasa total      : {resultado[2]:.3f}%")
                print(f"  Tasa hombres    : {f'{resultado[3]:.3f}%' if resultado[3] else 'N/D'}")
                print(f"  Tasa mujeres    : {f'{resultado[4]:.3f}%' if resultado[4] else 'N/D'}")

            print("\n" + "=" * 60)
            print("MIGRACION COMPLETADA EXITOSAMENTE")
            print("=" * 60)

except Error as e:
    print(f"ERROR MySQL: {e}")
    print("\nPosibles soluciones:")
    print("  1. Verifica credenciales y que el servidor este activo")
    print("  2. Revisa que los nombres de columnas del CSV coincidan")