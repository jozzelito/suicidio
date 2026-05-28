import pandas as pd

def cargar_datos(archivo):

    print(f"cargando{archivo}...")
    df = pd.read_csv(archivo)
    print(f"{df.shape[0]} filas,{df.shape[1]} columnas")
    return df

def filtrar_anios(df, year_date_min=2010, year_date_max=2024):
    print(f"\nFILTRANDO AÑOS {year_date_min} - {year_date_max}...")
    df['AÑO'] = df['AÑO'].astype(int)
    df = df[(df['AÑO'] >= year_date_min) & (df['AÑO'] <= year_date_max)]
    print(f"   Datos despues del filtro: {df.shape[0]} filas")
    print(f"   Rango de años: {df['AÑO'].min()} a {df['AÑO'].max()}")
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

    columnas_a_quitar = ['_id']

    # solo quitar las que existen

    columnas_existentes = [col for col in columnas_a_quitar if col in df.columns]
    df = df.drop(columns = columnas_existentes)

    print(f" quitadas {len(columnas_existentes)} columnas")
    print(f" columnas restantes: {df.shape[1]}")
    return df

def renombrar_columnas(df):
    print("\n Renombrando columnas...")

    nombres = {
        'CVE_ENT': 'cve_ent',
        'AÑO': 'year_date',
        'ENTIDAD': 'ent_name',
        'HOMBRES': 'male_suicides',
        'MUJERES': 'women_suicides',
        'TOTAL': 'total_suicides',
        'POBLACION_HOMBRES': 'male_pop',
        'POBLACION_MUJERES': 'female_pop',
        'DESCONOCIDO': 'unknown_gender',
        'POBLACION_TOTAL': 'poblation',
        'TASA_HOMBRES': 'male_rate',
        'TASA_MUJERES': 'female_rate',
        'TASA_TOTAL': 'suicide_rate'
    }

    #renombramos las que existen
    nombres_existentes = {k: v for k, v in nombres.items() if k in df.columns}
    df = df.rename(columns = nombres_existentes)

    print(f" Nuevas columnas: {list(df.columns)}")
    return df

def convertir_tipos(df):
    print("\n convirtiendo tipos de datos..")

    #columnas enteras
    columnas_int = ['year_date', 'male_suicides', 'female_suicides', 'total_suicides']
    for col in columnas_int:
        if col in df.columns:
            df[col] = df[col].astype(int)
    # columnas flotantes
    columnas_float = ['poblation','male_rate','female_rate','suicide_rate']
    for col in columnas_float:
        if col in df.columns:
            df[col] = df[col].astype(float)
    print(" Tipos convertidos correctamente")
    return df

def normalizar_estados(df):
    print("\n Normalizando nombres de estados...")

    if 'ent_name' in df.columns:
        df['ent_name'] = df['ent_name'].str.upper().str.strip()
        print(f" Estados unicos: {df['ent_name'].nunique()}")
        print(f" Ejemplos: {df['ent_name'].unique()[:5]}")

    return df

def verificar_calidad(df):

    print(f"\n verificando calidad de datos...")

    #tasas negativas
    if 'suicide_rate' in df.columns:
        negativas = (df['suicide_rate'] < 0).sum()
        if negativas > 0:
            print(f" {negativas} tasas negativas encontradas, corrigiendo...")
            df['suicide_rate'] = df['suicide_rate'] = df['suicide_rate'].abs()

    #verificar años
    if 'year_date' in df.columns:
        print(f"    Rango de años: {df['year_date'].min()} - {df['year_date'].max()}")

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


def analizar_datos(df):
    print("\n" + "=" * 60)
    print(" ANALISIS DE DATOS (2010-2024)")
    print("=" * 60)

    #=========================================================================================
    # 1. TOP 5 TASAS MAS ALTAS
    print("\n1. TOP 5 TASAS DE SUICIDIO MAS ALTAS:")
    top_5 = df.nlargest(5, 'suicide_rate')
    for i, row in top_5.iterrows():
        print(f"   {i + 1}. {row['ent_name']} ({row['year_date']}): {row['suicide_rate']:.2f}")
    #========================================================================================
    # 2. TOP 5 TASAS MAS BAJAS
    print("\n2. TOP 5 TASAS DE SUICIDIO MAS BAJAS:")
    bottom_5 = df.nsmallest(5, 'suicide_rate')
    for i, row in bottom_5.iterrows():
        print(f"   {i + 1}. {row['ent_name']} ({row['year_date']}): {row['suicide_rate']:.2f}")
    #======================================================================================
    # 3. AÑO CON MAYOR TASA
    print("\n3. AÑO CON MAYOR TASA DE SUICIDIO:")
    df_nacional = df[df['ent_name'] == 'NACIONAL']
    año_max = df_nacional.loc[df_nacional['suicide_rate'].idxmax()]
    print(f"   {año_max['year_date']} con tasa de {año_max['suicide_rate']:.2f}")

    #=======================================================================================
    # 4. GENERO CON TASA MAS ALTA
    print("\n4. GENERO CON TASA DE SUICIDIO MAS ALTA:")
    male_avg = df_nacional['male_rate'].mean()
    female_avg = df_nacional['female_rate'].mean()
    print(f"   HOMBRES: {male_avg:.2f}")
    print(f"   MUJERES: {female_avg:.2f}")
    #=========================================================================================
    # 5. TOP 5 ESTADOS 2024 Y GENERO PREDOMINANTE
    print("\n5. TOP 5 ESTADOS (2024) Y GENERO PREDOMINANTE:")
    df_2024 = df[(df['year_date'] == 2024) & (df['ent_name'] != 'NACIONAL')]
    top_5_2024 = df_2024.nlargest(5, 'suicide_rate')
    for i, row in top_5_2024.iterrows():
        if row['male_rate'] > row['female_rate']:
            print(f"   {i + 1}. {row['ent_name']}: {row['suicide_rate']:.2f} -> Predomina HOMBRES")
        else:
            print(f"   {i + 1}. {row['ent_name']}: {row['suicide_rate']:.2f} -> Predomina MUJERES")
#============================================

def pipeline_limpieza(archivo_entrada):
    print("=" * 60)
    print(" PROCESO DE LIMPIEZA DE DATOS")
    print("=" * 60)

    df = cargar_datos(archivo_entrada)
    df = eliminar_nulos(df)
    df = filtrar_anios(df)
    df = eliminar_duplicados(df)
    df = eliminar_columnas_innecesarias(df)
    df = renombrar_columnas(df)
    df = convertir_tipos(df)
    df = normalizar_estados(df)
    df = verificar_calidad(df)
    mostrar_resumen(df)
    guardar_datos_limpios(df)
    analizar_datos(df)

    return df

if __name__ == "__main__":
    df_limpio = pipeline_limpieza(('datos_suicidio_api.csv'))

    print("\n" + "=" * 60)
    print(" PROCESO DE LIMPIEZA COMPLETADO")
    print("=" * 60)