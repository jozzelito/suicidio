import pymysql
from pymongo import MongoClient
from decimal import Decimal

# Configuracion
mysql_conn = pymysql.connect(
    host="127.0.0.1",
    user="root",
    password="Tocino",
    port=3306,
    database="suicide_rate"
)

mongo_client = MongoClient("mongodb://localhost:27017/")
mongo_db = mongo_client["suicide_rate"]


def convertir_para_mongodb(datos):
    ## Convierte tipos no soportados por MongoDB (como Decimal) a tipos soportados
    if isinstance(datos, dict):
        # Para diccionarios (cada fila de la tabla)
        nuevo_dict = {}
        for key, value in datos.items():
            if isinstance(value, Decimal):
                nuevo_dict[key] = float(value)  # Decimal -> float
            elif isinstance(value, (list, tuple)):
                nuevo_dict[key] = [convertir_para_mongodb(item) for item in value]
            elif isinstance(value, dict):
                nuevo_dict[key] = convertir_para_mongodb(value)
            else:
                nuevo_dict[key] = value
        return nuevo_dict
    elif isinstance(datos, list):
        # Para listas de filas
        return [convertir_para_mongodb(item) for item in datos]
    else:
        return datos


def migrar_tabla(nombre_tabla):
    ## Migra una tabla especifica manejando los tipos de datos
    try:
        with mysql_conn.cursor(pymysql.cursors.DictCursor) as cursor:
            print(f"  Leyendo datos de '{nombre_tabla}'...", end=" ")
            cursor.execute(f"SELECT * FROM `{nombre_tabla}`")
            rows = cursor.fetchall()

            if not rows:
                print(f"Sin datos")
                return

            # Convertir Decimal a float para MongoDB
            print(f"procesando {len(rows)} registros...", end=" ")
            rows_convertidos = convertir_para_mongodb(rows)

            # Insertar en MongoDB
            mongo_db[nombre_tabla].insert_many(rows_convertidos)
            print(f"Migrada ({len(rows)} documentos)")

    except pymysql.Error as e:
        # Error especifico de MySQL (como el GROUP BY)
        if "sql_mode=only_full_group_by" in str(e):
            print(f"  '{nombre_tabla}': La vista tiene problemas con GROUP BY")
            print(f"     Sugerencia: Modifica la vista o ejecuta: SET sql_mode=''")
        else:
            print(f"  MySQL Error en '{nombre_tabla}': {e}")
    except Exception as e:
        print(f"  Error en '{nombre_tabla}': {e}")

def migrar_vista_especial(nombre_vista):
    ## Version especial para vistas que pueden tener problemas
    try:
        with mysql_conn.cursor(pymysql.cursors.DictCursor) as cursor:
            # Intentar resolver temporalmente el problema de GROUP BY
            cursor.execute("SET sql_mode = ''")
            cursor.execute(f"SELECT * FROM `{nombre_vista}`")
            rows = cursor.fetchall()

            if rows:
                rows_convertidos = convertir_para_mongodb(rows)
                mongo_db[nombre_vista].insert_many(rows_convertidos)
                print(f"  Vista '{nombre_vista}' migrada ({len(rows)} documentos)")
            else:
                print(f"  Vista '{nombre_vista}' sin datos")

    except Exception as e:
        print(f"  Error en vista '{nombre_vista}': {e}")

def obtener_todas_las_tablas():
    ## Obtiene todas las tablas y vistas de MySQL
    with mysql_conn.cursor() as cursor:
        cursor.execute("SHOW FULL TABLES")
        resultados = cursor.fetchall()

        tablas = []
        vistas = []

        for resultado in resultados:
            nombre = resultado[0]
            tipo = resultado[1]
            if tipo == 'BASE TABLE':
                tablas.append(nombre)
            elif tipo == 'VIEW':
                vistas.append(nombre)

        return tablas, vistas

def main():
    print("MIGRANDO suicide_rate DE MySQL A MongoDB\n")
    print("=" * 60)

    # Obtener tablas y vistas
    tablas, vistas = obtener_todas_las_tablas()

    print(f"TABLAS encontradas ({len(tablas)}):")
    for tabla in tablas:
        print(f"   - {tabla}")

    print(f"\nVISTAS encontradas ({len(vistas)}):")
    for vista in vistas:
        print(f"   - {vista}")

    print("\n" + "=" * 60)
    print("INICIANDO MIGRACION...\n")

    # Migrar tablas normales primero
    print("MIGRANDO TABLAS:")
    for tabla in tablas:
        migrar_tabla(tabla)

    # Migrar vistas (con manejo especial)
    if vistas:
        print("\nMIGRANDO VISTAS:")
        for vista in vistas:
            if 'vw_average_per_decade_national' in vista:
                migrar_vista_especial(vista)
            else:
                migrar_tabla(vista)

    # Resumen final
    print("\n" + "=" * 60)
    print("RESUMEN FINAL:")

    todas_colecciones = tablas + vistas
    for coleccion in todas_colecciones:
        if coleccion in mongo_db.list_collection_names():
            count = mongo_db[coleccion].count_documents({})
            print(f"   {coleccion}: {count} documentos")
        else:
            print(f"   {coleccion}: No migrada")

    # Cerrar conexiones
    mysql_conn.close()
    mongo_client.close()

    print("\nPROCESO COMPLETADO")

if __name__ == "__main__":
    main()