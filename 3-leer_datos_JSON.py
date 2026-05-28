import pandas as pd
import requests

# 1. Datos del Banco Mundial desde API (solo 2010-2024)
url = "https://api.worldbank.org/v2/country/mx/indicator/SL.UEM.TOTL.ZS?format=json"
df_bm = pd.DataFrame([
    {'year_date': int(d['date']), 'rate_total': d['value']}
    for d in requests.get(url).json()[1]
    if d['value'] is not None and 2010 <= int(d['date']) <= 2024
])

# 2. Datos de género desde CSV (solo lectura desde Descargas, filtrando 2010-2024)
ruta_csv = r"C:\Users\sandy\Downloads\desempleo_por_genero.csv"
df_gen = pd.read_csv(ruta_csv, skiprows=4, encoding='latin1')
df_gen.columns = ['anio', 'mes', 'rate_male', 'rate_female', 'p_male', 'p_female', 'o_male', 'o_female']
df_gen = df_gen[df_gen['anio'].astype(str).str.isnumeric()]
df_gen['anio'] = df_gen['anio'].astype(int)
df_gen = df_gen[(df_gen['anio'] >= 2010) & (df_gen['anio'] <= 2024)]
df_gen['rate_male'] = pd.to_numeric(df_gen['rate_male'], errors='coerce')
df_gen['rate_female'] = pd.to_numeric(df_gen['rate_female'], errors='coerce')

# Calcular promedios anuales y renombrar columna
df_promedio = df_gen.groupby('anio')[['rate_male', 'rate_female']].mean().round(2).reset_index()
df_promedio = df_promedio.rename(columns={'anio': 'year_date'})

# 3. Combinar y guardar en Python
df_final = pd.merge(df_bm, df_promedio, on='year_date', how='outer')
df_final = df_final[['year_date', 'rate_total', 'rate_male', 'rate_female']]
df_final = df_final.sort_values('year_date', ascending=False)

# Guardar el CSV
df_final.to_csv('desempleo_completo_mexico.csv', index=False, encoding='utf-8-sig')

print("El CSV fue guardado como 'desempleo_completo_mexico.csv'")
print(df_final)