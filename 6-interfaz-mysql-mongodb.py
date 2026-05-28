import tkinter as tk
from tkinter import ttk, messagebox
import threading
import pandas as pd
from mysql.connector import connect, Error
import os
from contextlib import closing
import pymysql
from pymongo import MongoClient
from decimal import Decimal


class MigrationApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Migration Manager - MySQL ↔ MongoDB")
        self.root.geometry("1400x700")
        self.root.configure(bg='#2b2b2b')

        # Variables de conexión
        self.mysql_host = tk.StringVar(value="127.0.0.1")
        self.mysql_user = tk.StringVar(value="root")
        self.mysql_pass = tk.StringVar(value="Tocino")
        self.mysql_port = tk.IntVar(value=3306)
        self.mysql_db = tk.StringVar(value="suicide_rate")

        self.mongo_host = tk.StringVar(value="localhost")
        self.mongo_port = tk.IntVar(value=27017)
        self.mongo_db = tk.StringVar(value="suicide_rate")

        # Configurar la interfaz
        self.setup_ui()

    def setup_ui(self):
        # Frame principal
        main_frame = tk.Frame(self.root, bg='#2b2b2b')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # ========== CONFIGURACION DE CONEXIONES ==========
        config_frame = tk.LabelFrame(main_frame, text="Configuracion de Conexiones",
                                     bg='#3c3c3c', fg='white', font=('Arial', 12, 'bold'))
        config_frame.pack(fill=tk.X, padx=5, pady=5)

        # MySQL Configuration
        mysql_frame = tk.Frame(config_frame, bg='#3c3c3c')
        mysql_frame.pack(side=tk.LEFT, padx=20, pady=10, fill=tk.BOTH, expand=True)

        tk.Label(mysql_frame, text="MySQL Configuration", bg='#3c3c3c', fg='#4CAF50',
                 font=('Arial', 10, 'bold')).pack(anchor=tk.W)

        self.create_config_row(mysql_frame, "Host:", self.mysql_host, 0)
        self.create_config_row(mysql_frame, "User:", self.mysql_user, 1)
        self.create_config_row(mysql_frame, "Password:", self.mysql_pass, 2, show='*')
        self.create_config_row(mysql_frame, "Port:", self.mysql_port, 3)
        self.create_config_row(mysql_frame, "Database:", self.mysql_db, 4)

        # MongoDB Configuration
        mongo_frame = tk.Frame(config_frame, bg='#3c3c3c')
        mongo_frame.pack(side=tk.RIGHT, padx=20, pady=10, fill=tk.BOTH, expand=True)

        tk.Label(mongo_frame, text="MongoDB Configuration", bg='#3c3c3c', fg='#FF9800',
                 font=('Arial', 10, 'bold')).pack(anchor=tk.W)

        self.create_config_row(mongo_frame, "Host:", self.mongo_host, 0)
        self.create_config_row(mongo_frame, "Port:", self.mongo_port, 1)
        self.create_config_row(mongo_frame, "Database:", self.mongo_db, 2)

        # ========== BOTONES DE ACCION ==========
        buttons_frame = tk.Frame(main_frame, bg='#2b2b2b')
        buttons_frame.pack(fill=tk.X, padx=5, pady=10)

        self.btn_mysql = tk.Button(buttons_frame, text="1. EJECUTAR MYSQL (Crear BD y cargar datos)",
                                   command=self.run_mysql_code, bg='#4CAF50', fg='white',
                                   font=('Arial', 11, 'bold'), height=2, cursor='hand2')
        self.btn_mysql.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        self.btn_mongo = tk.Button(buttons_frame, text="2. EJECUTAR MIGRACION (MySQL -> MongoDB)",
                                   command=self.run_migration, bg='#FF9800', fg='white',
                                   font=('Arial', 11, 'bold'), height=2, cursor='hand2')
        self.btn_mongo.pack(side=tk.RIGHT, padx=5, fill=tk.X, expand=True)

        # ========== PANEL DE ESTADO ==========
        status_frame = tk.LabelFrame(main_frame, text="Estado de Bases de Datos",
                                     bg='#3c3c3c', fg='white', font=('Arial', 12, 'bold'))
        status_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Frame contenedor para los dos paneles
        paned_window = tk.PanedWindow(status_frame, orient=tk.HORIZONTAL, bg='#3c3c3c', sashrelief='sunken')
        paned_window.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Panel MySQL (izquierdo)
        mysql_panel = tk.Frame(paned_window, bg='#3c3c3c')
        paned_window.add(mysql_panel, width=650)

        tk.Label(mysql_panel, text="MySQL - Estructura", bg='#3c3c3c', fg='#4CAF50',
                 font=('Arial', 11, 'bold')).pack(pady=5)

        # Frame para Treeview y scrollbar de MySQL
        mysql_tree_frame = tk.Frame(mysql_panel, bg='#3c3c3c')
        mysql_tree_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.mysql_tree = ttk.Treeview(mysql_tree_frame, show='tree', height=20)
        self.mysql_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scroll_mysql = ttk.Scrollbar(mysql_tree_frame, orient='vertical', command=self.mysql_tree.yview)
        scroll_mysql.pack(side=tk.RIGHT, fill=tk.Y)
        self.mysql_tree.configure(yscrollcommand=scroll_mysql.set)

        # Botones de MySQL
        mysql_buttons_frame = tk.Frame(mysql_panel, bg='#3c3c3c')
        mysql_buttons_frame.pack(fill=tk.X, pady=5)

        tk.Button(mysql_buttons_frame, text="Refrescar MySQL", command=self.refresh_mysql_structure,
                  bg='#4CAF50', fg='white', cursor='hand2', font=('Arial', 9)).pack(side=tk.LEFT, padx=5)

        # Panel MongoDB (derecho)
        mongo_panel = tk.Frame(paned_window, bg='#3c3c3c')
        paned_window.add(mongo_panel, width=650)

        tk.Label(mongo_panel, text="MongoDB - Colecciones", bg='#3c3c3c', fg='#FF9800',
                 font=('Arial', 11, 'bold')).pack(pady=5)

        # Frame para Treeview y scrollbar de MongoDB
        mongo_tree_frame = tk.Frame(mongo_panel, bg='#3c3c3c')
        mongo_tree_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.mongo_tree = ttk.Treeview(mongo_tree_frame, show='tree', height=20)
        self.mongo_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scroll_mongo = ttk.Scrollbar(mongo_tree_frame, orient='vertical', command=self.mongo_tree.yview)
        scroll_mongo.pack(side=tk.RIGHT, fill=tk.Y)
        self.mongo_tree.configure(yscrollcommand=scroll_mongo.set)

        # Botones de MongoDB
        mongo_buttons_frame = tk.Frame(mongo_panel, bg='#3c3c3c')
        mongo_buttons_frame.pack(fill=tk.X, pady=5)

        tk.Button(mongo_buttons_frame, text="Refrescar MongoDB", command=self.refresh_mongo_structure,
                  bg='#FF9800', fg='white', cursor='hand2', font=('Arial', 9)).pack(side=tk.LEFT, padx=5)

        # Barra de estado
        self.status_bar = tk.Label(main_frame, text="Listo", bd=1, relief=tk.SUNKEN, anchor=tk.W,
                                   bg='#3c3c3c', fg='white')
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        # Cargar estructuras iniciales
        self.refresh_mysql_structure()
        self.refresh_mongo_structure()

    def update_status(self, message):
        """Actualiza la barra de estado"""
        self.status_bar.config(text=message)
        self.status_bar.update_idletasks()

    def create_config_row(self, parent, label_text, variable, row, show=None):
        """Crea una fila de configuracion"""
        frame = tk.Frame(parent, bg='#3c3c3c')
        frame.pack(fill=tk.X, pady=2)

        tk.Label(frame, text=label_text, width=12, anchor=tk.W,
                 bg='#3c3c3c', fg='white').pack(side=tk.LEFT)

        entry = tk.Entry(frame, textvariable=variable, width=30, bg='#4a4a4a',
                         fg='white', insertbackground='white')
        if show:
            entry.config(show=show)
        entry.pack(side=tk.LEFT, padx=5)

    def run_mysql_code(self):
        """Ejecuta el codigo MySQL en un hilo separado"""
        if messagebox.askyesno("Confirmar", "Ejecutar el codigo MySQL?\nEsto creara la BD y cargara los datos."):
            threading.Thread(target=self._run_mysql_thread, daemon=True).start()

    def _run_mysql_thread(self):
        """Thread para ejecutar codigo MySQL"""
        self.btn_mysql.config(state=tk.DISABLED, text="Ejecutando MySQL...")
        self.update_status("Ejecutando codigo MySQL...")

        try:
            self.execute_mysql_code()
            self.update_status("MySQL ejecutado exitosamente")
            messagebox.showinfo("Exito", "MySQL ejecutado correctamente")
            self.refresh_mysql_structure()

        except Exception as e:
            self.update_status(f"Error: {str(e)}")
            messagebox.showerror("Error MySQL", str(e))
        finally:
            self.btn_mysql.config(state=tk.NORMAL, text="1. EJECUTAR MYSQL (Crear BD y cargar datos)")

    def execute_mysql_code(self):
        """Implementacion del codigo MySQL"""
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        CSV_SUICIDIO = os.path.join(BASE_DIR, 'datos_suicidio_limpios.csv')

        try:
            with connect(
                    host=self.mysql_host.get(),
                    user=self.mysql_user.get(),
                    password=self.mysql_pass.get(),
                    port=self.mysql_port.get()
            ) as conexion:
                with closing(conexion.cursor()) as cursor:
                    # Verificar/Crear base de datos
                    cursor.execute("SELECT COUNT(*) FROM information_schema.schemata WHERE schema_name = %s",
                                   (self.mysql_db.get(),))
                    if cursor.fetchone()[0] == 0:
                        cursor.execute(
                            f"CREATE DATABASE {self.mysql_db.get()} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")

                    cursor.execute(f"USE {self.mysql_db.get()}")

                    # Verificar si ya hay datos
                    cursor.execute("SHOW TABLES")
                    tables = cursor.fetchall()

                    if not tables and os.path.exists(CSV_SUICIDIO):
                        df_suicidio = pd.read_csv(CSV_SUICIDIO)

                        # Crear tabla entity
                        cursor.execute("""
                            CREATE TABLE IF NOT EXISTS entity (
                                cve_entity TINYINT UNSIGNED NOT NULL PRIMARY KEY,
                                ent_name VARCHAR(60) NOT NULL,
                                is_national BOOLEAN NOT NULL DEFAULT FALSE
                            )
                        """)

                        # Insertar datos
                        entities = df_suicidio[['cve_ent', 'ent_name']].drop_duplicates()
                        for _, row in entities.iterrows():
                            is_national = 1 if row['cve_ent'] == 0 else 0
                            cursor.execute("INSERT IGNORE INTO entity VALUES (%s, %s, %s)",
                                           (int(row['cve_ent']), row['ent_name'], is_national))
                        conexion.commit()

        except Error as e:
            raise e

    def run_migration(self):
        """Ejecuta la migracion MySQL -> MongoDB"""
        if messagebox.askyesno("Confirmar", "Ejecutar migracion de MySQL a MongoDB?\nEsto copiara todos los datos."):
            threading.Thread(target=self._run_migration_thread, daemon=True).start()

    def _run_migration_thread(self):
        """Thread para ejecutar migracion"""
        self.btn_mongo.config(state=tk.DISABLED, text="Migrando datos...")
        self.update_status("Migrando datos de MySQL a MongoDB...")

        try:
            # Conectar a MySQL
            mysql_conn = pymysql.connect(
                host=self.mysql_host.get(),
                user=self.mysql_user.get(),
                password=self.mysql_pass.get(),
                port=self.mysql_port.get(),
                database=self.mysql_db.get()
            )

            # Conectar a MongoDB
            mongo_client = MongoClient(f"mongodb://{self.mongo_host.get()}:{self.mongo_port.get()}/")
            mongo_db = mongo_client[self.mongo_db.get()]

            # Obtener tablas y vistas
            with mysql_conn.cursor() as cursor:
                cursor.execute("SHOW FULL TABLES")
                resultados = cursor.fetchall()
                tablas = [r[0] for r in resultados if r[1] == 'BASE TABLE']
                vistas = [r[0] for r in resultados if r[1] == 'VIEW']

            # Migrar tablas
            for tabla in tablas:
                self.migrar_tabla(mysql_conn, mongo_db, tabla)

            # Migrar vistas
            for vista in vistas:
                self.migrar_tabla(mysql_conn, mongo_db, vista)

            self.update_status("Migracion completada exitosamente")
            messagebox.showinfo("Exito", "Migracion completada correctamente")
            self.refresh_mongo_structure()

            mysql_conn.close()
            mongo_client.close()

        except Exception as e:
            self.update_status(f"Error en migracion: {str(e)}")
            messagebox.showerror("Error Migracion", str(e))
        finally:
            self.btn_mongo.config(state=tk.NORMAL, text="2. EJECUTAR MIGRACION (MySQL -> MongoDB)")

    def migrar_tabla(self, mysql_conn, mongo_db, nombre_tabla):
        """Migra una tabla especifica"""
        try:
            with mysql_conn.cursor(pymysql.cursors.DictCursor) as cursor:
                cursor.execute(f"SELECT * FROM `{nombre_tabla}`")
                rows = cursor.fetchall()

                if rows:
                    rows_convertidos = self.convertir_para_mongodb(rows)
                    mongo_db[nombre_tabla].insert_many(rows_convertidos)

        except Exception as e:
            print(f"Error en {nombre_tabla}: {e}")

    def convertir_para_mongodb(self, datos):
        """Convierte tipos no soportados por MongoDB"""
        if isinstance(datos, dict):
            nuevo_dict = {}
            for key, value in datos.items():
                if isinstance(value, Decimal):
                    nuevo_dict[key] = float(value)
                elif isinstance(value, (list, tuple)):
                    nuevo_dict[key] = [self.convertir_para_mongodb(item) for item in value]
                elif isinstance(value, dict):
                    nuevo_dict[key] = self.convertir_para_mongodb(value)
                else:
                    nuevo_dict[key] = value
            return nuevo_dict
        elif isinstance(datos, list):
            return [self.convertir_para_mongodb(item) for item in datos]
        else:
            return datos

    def refresh_mysql_structure(self):
        """Refresca el arbol de MySQL"""
        for item in self.mysql_tree.get_children():
            self.mysql_tree.delete(item)

        try:
            with connect(
                    host=self.mysql_host.get(),
                    user=self.mysql_user.get(),
                    password=self.mysql_pass.get(),
                    port=self.mysql_port.get(),
                    database=self.mysql_db.get()
            ) as conexion:
                with closing(conexion.cursor()) as cursor:
                    cursor.execute("SHOW FULL TABLES")
                    tables = cursor.fetchall()

                    tablas_node = self.mysql_tree.insert("", "end", text="Tablas", open=True)
                    vistas_node = self.mysql_tree.insert("", "end", text="Vistas", open=True)
                    sp_node = self.mysql_tree.insert("", "end", text="Stored Procedures", open=True)
                    triggers_node = self.mysql_tree.insert("", "end", text="Triggers", open=True)

                    for table in tables:
                        nombre = table[0]
                        tipo = table[1]
                        try:
                            if tipo == 'BASE TABLE':
                                cursor.execute(f"SELECT COUNT(*) FROM `{nombre}`")
                                count = cursor.fetchone()[0]
                                self.mysql_tree.insert(tablas_node, "end", text=f"{nombre} ({count:,} registros)")
                            elif tipo == 'VIEW':
                                self.mysql_tree.insert(vistas_node, "end", text=nombre)
                        except:
                            self.mysql_tree.insert(tablas_node, "end", text=f"{nombre} (acceso denegado)")

                    # Obtener Stored Procedures
                    try:
                        cursor.execute("""
                            SELECT ROUTINE_NAME FROM information_schema.ROUTINES 
                            WHERE ROUTINE_SCHEMA = %s AND ROUTINE_TYPE = 'PROCEDURE'
                        """, (self.mysql_db.get(),))
                        sps = cursor.fetchall()
                        for sp in sps:
                            self.mysql_tree.insert(sp_node, "end", text=sp[0])
                    except:
                        pass

                    # Obtener Triggers
                    try:
                        cursor.execute("""
                            SELECT TRIGGER_NAME FROM information_schema.TRIGGERS 
                            WHERE TRIGGER_SCHEMA = %s
                        """, (self.mysql_db.get(),))
                        triggers = cursor.fetchall()
                        for trigger in triggers:
                            self.mysql_tree.insert(triggers_node, "end", text=trigger[0])
                    except:
                        pass

                    stats_node = self.mysql_tree.insert("", "end", text="Estadisticas", open=True)
                    cursor.execute("SELECT COUNT(*) FROM information_schema.TABLES WHERE TABLE_SCHEMA = %s",
                                   (self.mysql_db.get(),))
                    total_tables = cursor.fetchone()[0]
                    self.mysql_tree.insert(stats_node, "end", text=f"Total de tablas: {total_tables}")

        except Exception as e:
            self.mysql_tree.insert("", "end", text=f"Error de conexion: {e}")

    def refresh_mongo_structure(self):
        """Refresca el arbol de MongoDB"""
        for item in self.mongo_tree.get_children():
            self.mongo_tree.delete(item)

        try:
            mongo_client = MongoClient(f"mongodb://{self.mongo_host.get()}:{self.mongo_port.get()}/")
            mongo_db = mongo_client[self.mongo_db.get()]

            colecciones = mongo_db.list_collection_names()

            if colecciones:
                stats_node = self.mongo_tree.insert("", "end", text="Estadisticas", open=True)
                self.mongo_tree.insert(stats_node, "end", text=f"Total de colecciones: {len(colecciones)}")

                colecciones_node = self.mongo_tree.insert("", "end", text="Colecciones", open=True)

                for coleccion in colecciones:
                    count = mongo_db[coleccion].count_documents({})
                    try:
                        stats = mongo_db.command("collstats", coleccion)
                        size_mb = stats['size'] / (1024 * 1024)
                        self.mongo_tree.insert(colecciones_node, "end",
                                               text=f"{coleccion} ({count:,} docs, {size_mb:.2f} MB)")
                    except:
                        self.mongo_tree.insert(colecciones_node, "end",
                                               text=f"{coleccion} ({count:,} docs)")
            else:
                self.mongo_tree.insert("", "end", text="No hay colecciones (ejecute migracion primero)")

            mongo_client.close()

        except Exception as e:
            self.mongo_tree.insert("", "end", text=f"Error de conexion: {e}")


if __name__ == "__main__":
    root = tk.Tk()
    app = MigrationApp(root)
    root.mainloop()