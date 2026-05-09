import pandas as pd

def cargar_datos(archivo):

    print(f"cargando{archivo}...")
    df = pd.read_csv(archivo)
    print(f"{df.shape[0]} filas,{df.shape[1]} columnas")
    return df

def eliminar_nulos(df):

    print("\n Eliminando valores nulos")
    antes = len(df)
    df = df.dropna()
    despues = len(df)
    print(f"eliminando {antes - despues} filas con nulos")
    return df

def eliminar_duplicados(df):

    print("\n Eliminando duplicados...")
    antes = len(df)
    df = df.drop_duplicates()
    despues = len(df)
    print(f" eliminadas {antes - despues} filas duplicadas")
    return df

def eliminar_columnas_innecesarias(df):

    print("\n Eliminando columnas innecearias...")
    columnas_originales = df.shape[1]

    columnas_a_quitar = ['_id', 'CVE_ENT', 'DESCONOCIDO',
                         'POBLACION_HOMBRES','POBLACION_MUJERES']

    # solo quitar las que existen

    columnas_existentes = [col for col in columnas_a_quitar if col in df.columns]
    df = df.drop(columns = columnas_existentes)

    print(f" quitadas {len(columnas_existentes)} columnas")
    print(f" columnas restantes: {df.shape[1]}")
    return df

def renombrar_columnas(df):
    print("\n Renombrando columnas...")

    nombres = {
        'AÑO': 'anio',
        'ENTIDAD': 'estado',
        'HOMBRES': 'suicidios_hombres',
        'MUJERES': 'suicidios_mujeres',
        'TOTAL': 'suicidios_total',
        'POBLACION_TOTAL': 'poblacion',
        'TASA_HOMBRES': 'tasa_hombres',
        'TASA_MUJERES': 'tasa_mujeres',
        'TASA_TOTAL': 'tasa_suicidio'
    }

    #renombramos las que existen
    nombres_existentes = {k: v for k, v in nombres.items() if k in df.columns}
    df = df.rename(columns = nombres_existentes)

    print(f" Nuevas columnas: {list(df.columns)}")
    return df

def convertir_tipos(df):
    print("\n convirtiendo tipos de datos..")

    #columnas enteras
    columnas_int = ['anio', 'suicidios_hombres', 'suicidios_mujeres', 'suicidios_total']
    for col in columnas_int:
        if col in df.columns:
            df[col] = df[col].astype(int)
    # columnas flotantes
    columnas_float = ['poblacion','tasa_hombres','tasa_mujeres','tasa_suicidio']
    for col in columnas_float:
        if col in df.columns:
            df[col] = df[col].astype(float)
    print(" Tipos convertidos correctamente")
    return df

def normalizar_estados(df):
    print("\n Normalizando nombres de estados...")

    if 'estado' in df.columns:
        df['estado'] = df['estado'].str.upper().str.strip()
        print(f" Estados unicos: {df['estado'].nunique()}")
        print(f" Ejemplos: {df['estado'].unique()[:5]}")

    return df

def verificar_calidad(df):

    print(f"\n verificando calidad de datos...")

    #tasas negativas
    if 'tasa_suicidio' in df.columns:
        negativas = (df['tasa_suicidio'] < 0).sum()
        if negativas > 0:
            print(f" {negativas} tasas negativas encontradas, corrigiendo...")
            df['tasa_suicidio'] = df['tasa_suicidio'] = df['tasa_suicidio'].abs()

    #verificar años
    if 'anio' in df.columns:
        print(f"    Rango de años: {df['anio'].min()} - {df['anio'].max()}")

    #verificar poblacion
    if 'poblacion' in df.columns:
        print(f" Poblacion total: {df['poblacion'].sum():,.0f}")

    print(" Verificacion completada")
    return df

def mostrar_resumen(df):

    print("\n" + "=" * 60)
    print(" RESUMEN FINAL DE DATOS LIMPIOS")
    print("=" * 60)

    print(f"\n Dimensiones: {df.shape[0]} filas x {df.shape[1]} columnas")

    print(f" \n columnas finales")
    for i, col in enumerate(df.columns, 1):
        print(f"\n  {i:2}. {col}")

    print(f"\n primera 5 filas:")
    print(df.head())

    print(f"\n estadisticas basicas:")
    print(df.describe())

def guardar_datos_limpios(df, archivo_salida = 'datos_suicidio_limpios.csv'):
    df.to_csv(archivo_salida, index=False)
    print(f"\n Datos limpios guardados en: {archivo_salida}")
    return archivo_salida

#============================================
#============================================

def pipeline_limpieza(archivo_entrada):
    print("=" * 60)
    print(" PROCESO DE LIMPIEZA DE DATOS")
    print("=" * 60)

    df = cargar_datos(archivo_entrada)
    df = eliminar_nulos(df)
    df = eliminar_duplicados(df)
    df = eliminar_columnas_innecesarias(df)
    df = renombrar_columnas(df)
    df = convertir_tipos(df)
    df = normalizar_estados(df)
    df = verificar_calidad(df)
    mostrar_resumen(df)
    guardar_datos_limpios(df)

    return df

if __name__ == "__main__":
    df_limpio = pipeline_limpieza('datos_suicidio.csv')

    print("\n" + "=" * 60)
    print(" PROCESO DE LIMPIEZA COMPLETADO")
    print("=" * 60)










