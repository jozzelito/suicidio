import requests
import pandas as pd

print("=" * 60)
print("LEYENDO DATOS API")
print("=" * 60)

#url de la API
url = 'https://datamx.io/api/3/action/datastore_search?resource_id=fc5e98c0-15a6-42f8-a6f9-67225bf48980&limit=32000'

response = requests.get(url)
datos = response.json()

df = pd.DataFrame(datos['result']['records'])

print(f"  Datos extraidos desde API: {len(df)} filas ")

print(" NOMBRES DE COLUMNAS:")
for i, col in enumerate(df.columns, 1):
    print(f"  {i}. {col}")

print("PRIMERAS 30 FILAS:")
print(df.head(30))

df.to_csv('datos_suicidio_api.csv', index=False)
print(" datos guardados en: datos_suicidio_api.csv")

print("ULTIMAS 10 FILAS:")
print(df.tail(10))


print("\n" + "=" * 60)
print(" INFORMACION")

print("\n DATOS DEL AÑO 2023:")
url_2023 = 'https://datamx.io/api/3/action/datastore_search?resource_id=fc5e98c0-15a6-42f8-a6f9-67225bf48980&filters={"AÑO":2023}&limit=100'
response_2023 = requests.get(url_2023)
df_2023 = pd.DataFrame(response_2023.json()['result']['records'])
print(f" registros encontrados: {len(df_2023)}")
print(df_2023[['ENTIDAD','TASA_TOTAL']].head(10))

#=============================================================================================================
print("\n DATOS DE CHIHUAHUA:")
url_chih = 'https://datamx.io/api/3/action/datastore_search?resource_id=fc5e98c0-15a6-42f8-a6f9-67225bf48980&filters={"ENTIDAD":"Chihuahua"}&limit=100'
response_chih = requests.get(url_chih)
df_chih = pd.DataFrame(response_chih.json()['result']['records'])
print(f" registros de chihuahua:{len(df_chih)}")
print(df_chih[['AÑO','TASA_TOTAL']].head(10))

#============================================================================
#TOP 10 TASAS MAS ALTAS, SUPER SI, SUPER WOOW, LA MAS DURA LA NUMBER ONE, TODAS QUIEREN ESTE LUGAR!!!
print(" TOP 10 TASAS MAS ALTAS:")
url_top = 'https://datamx.io/api/3/action/datastore_search?resource_id=fc5e98c0-15a6-42f8-a6f9-67225bf48980&sort=TASA_TOTAL desc&limit=10'
response_top = requests.get(url_top)
df_top = pd.DataFrame(response_top.json()['result']['records'])
for i, row in df_top.iterrows():
    print(f" {i+1}. {row['ENTIDAD']} ({row['AÑO']}) ({row['TASA_TOTAL']})")

#==============================================================================
#DATOS NACIONALES

print(" DATOS NACIONELES (MEXICO):")
url_nac = 'https://datamx.io/api/3/action/datastore_search?resource_id=fc5e98c0-15a6-42f8-a6f9-67225bf48980&filters=%7B"CVE_ENT":0%7D&limit=100'
response_nac = requests.get(url_nac)
df_nac = pd.DataFrame(response_nac.json()['result']['records'])
print( f"  evolucion nacional 1990-2024:")
for i, row in df_nac.tail(10).iterrows():
    print( f"  {row['AÑO']}:  {row['TASA_TOTAL']}")

print ("\n" + "=" * 60)
print(" INFORMACION")
print( "=" * 60)

#=========================================================================
