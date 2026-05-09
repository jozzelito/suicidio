import pandas as pd
from mysql.connector import connect, Error

print("=" * 60)
print(" ENVIANDO DATOS A MySQL")
print("=" * 60)

df = pd.read_csv('datos_suicidio_limpios.csv')
print(f"\n Datos cargados: {df.shape[0]} filas, {df.shape[1]} columnas")

def conectar():
    try:
        conexion = connect(
            host = "127.0.0.1",
            user = "root",
            password = "Tocino",
            database = "ProyectoSuicidio",
            port = 3306

        )
        print (f" Conectado a MySQL")
        return conexion
    except Error as e:
        print(f"Error de conexion: {e}")
        return None

def crear_tabla(conexion):
    cursor = conexion.cursor()

    sql = """
    CREATE TABLE IF NOT EXISTS SuicidiosMexico (
        id INT AUTO_INCREMENT PRIMARY KEY,
        anio INT,
        estado VARCHAR(100),
        suicidios_hombres  INT,
        suicidios_mujeres INT,
        suicidios_total INT,
        poblacion FLOAT,
        tasa_hombres FLOAT,
        tasa_mujeres FLOAT,
        tasa_suicidio FLOAT
   )
   """
    cursor.execute(sql)
    print(" Tabla 'SuicidiosMexico' creada o ya existe")
    cursor.close()

def insertar_datos(conexion, df):
    cursor = conexion.cursor()

    sql = """
    INSERT INTO SuicidiosMexico 
    (anio, estado, suicidios_hombres, suicidios_mujeres,
    suicidios_total, poblacion, tasa_hombres, tasa_mujeres,
    tasa_suicidio)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    datos = df[['anio', 'estado', 'suicidios_hombres', 'suicidios_mujeres',
                'suicidios_total', 'poblacion', 'tasa_hombres',
                'tasa_mujeres', 'tasa_suicidio']].values.tolist()
    cursor.executemany(sql, datos)
    conexion.commit()

    print(f" Insertados {len(datos)} registros en la tabla")
    cursor.close()

def consultar_ejemplos(conexion):
    cursor = conexion.cursor()

    print("\n" + "=" * 60)
    print(" CONSULTAS DE EJEMPLO")
    print("=" * 60)

    sql = """
    SELECT estado, anio, tasa_suicidio
    FROM SuicidiosMexico
    WHERE anio = (SELECT MAX(anio) FROM SuicidiosMexico)
    ORDER BY tasa_suicidio DESC
    LIMIT 5
    """
    cursor.execute(sql)
    print("\n top 5 estados con mayor tasa de suicidio(ultimo año):")
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[2]:.2f}")

    sql2="""
    SELECT anio, tasa_suicidio
    FROM SuicidiosMexico
    WHERE estado = 'NACIONAL'
    ORDER BY anio
    """
    cursor.execute(sql2)
    print("\n Tendencia nacional de suicidio:")
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]:.2f}")

    sql3 = """
    SELECT anio, tasa_suicidio
    FROM SuicidiosMexico
    WHERE estado = 'NACIONAL'
    ORDER BY tasa_suicidio DESC
    LIMIT 1
    """
    cursor.execute(sql3)
    row = cursor.fetchone()
    print(f"\n Año con MAYOR tasa nacional: {row[0]} con {row[1]:.2f}")

    cursor.close()

if __name__ == "__main__":
        conexion = conectar()

        if conexion:
            crear_tabla(conexion)
            insertar_datos(conexion, df)
            consultar_ejemplos(conexion)
            conexion.close()
            print("\n" + "=" * 60)
            print(" PROCESO COMPLETADO")
            print("=" * 60)
        else:
            print("\n No se pudo conectar a MySQL")
            print("Verifica:")
            print("  1. ¿MySQL está corriendo?")
            print("  2. ¿La contraseña es 'Tocino'?")
            print("  3. ¿La base de datos 'ProyectoSuicidio' existe?")



