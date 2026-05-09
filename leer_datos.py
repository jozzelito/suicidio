import pandas as pd

print("=" * 60)
print(" CARGANDO DATOS DE SUICIDIO EN MÉXICO")
print("=" * 60)

# Cargar el CSV
df = pd.read_csv('datos_suicidio.csv')

print("\n ARCHIVO CARGADO EXITOSAMENTE")
print(f"\n {df.shape[0]} filas y {df.shape[1]} columnas")

print("\n NOMBRES DE COLUMNAS:")
for i, col in enumerate(df.columns, 1):
    print(f"   {i}. {col}")

print("\n PRIMERAS 5 FILAS:")
print(df.head())

print("\n TIPOS DE DATOS:")
print(df.dtypes)