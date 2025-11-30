import os
import json
import requests
import csv
from tqdm import tqdm
from datetime import datetime
from urllib.parse import urlparse
import re

# ========== CONFIGURACIÓN ==========
API_KEY = "TU_API_KEY_AQUI"
BOARD_ID = "123456789"  # ID de tablero de ejemplo
COLUMN_IDS = ["archivo__1"] #, "archivo2__1", "archivo29__1", "archivo9__1", "archivo1__1", "archivo4__1", "archivo41__1", "archivo_mkmxnwg6"
STATUS_COLUMN_ID = "estado8__1"
NUM_SUC_COLUMN_ID = "n_meros__1"

HEADERS = {
    "Authorization": API_KEY,
    "Content-Type": "application/json"
}

DOWNLOAD_DIR = "DESCARGA_MONDAY"
LOG_DIR = "logs_descarga_monday"
CURSOR_FILE = "cursor_state.json"  # Archivo para guardar el estado del cursor

# Mapeo de IDs de columna a años (CRÍTICO)
COLUMN_TO_YEAR = {
    "archivo__1": "2018",
    #"archivo2__1": "2019", 
    #"archivo29__1": "2020",
    #"archivo9__1": "2021",
    #"archivo1__1": "2022",
    #"archivo4__1": "2023",
    #"archivo41__1": "2024",
    #"archivo_mkmxnwg6": "2025"
}

ABREVIATURAS = {
    "NOM-011-STPS-2001": "NOM_011",
    "NOM-015-STPS-2001": "NOM_015",
    "NOM-022-STPS-2015": "NOM_022",
    "NOM-025-STPS-2008": "NOM_025",
    "NOM-001-SEDE-2012": "NOM_001",
}

def limpiar_para_carpeta(texto):
    """Limpia texto para usar como nombre de carpeta - VERSIÓN MEJORADA"""
    if not texto:
        return "SIN_ESTADO"
    
    # Convertir a string y limpiar espacios
    texto_limpio = str(texto).strip()
    
    # Si está vacío después de limpiar espacios
    if not texto_limpio:
        return "SIN_ESTADO"
    
    # Remover caracteres problemáticos para nombres de carpeta
    texto_limpio = re.sub(r'[<>:"/\\|?*\r\n\t]', '_', texto_limpio)
    
    # Reemplazar múltiples espacios con un solo guión bajo
    texto_limpio = re.sub(r'\s+', '_', texto_limpio)
    
    # Limpiar guiones bajos al inicio y final
    texto_limpio = texto_limpio.strip('_')
    
    # Si queda vacío, usar valor por defecto
    return texto_limpio if texto_limpio else "SIN_ESTADO"

def cargar_estado_cursor():
    """Carga el estado del cursor desde archivo"""
    try:
        if os.path.exists(CURSOR_FILE):
            with open(CURSOR_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('cursor'), data.get('processed_items', set())
        return None, set()
    except Exception as e:
        print(f"⚠️ Error cargando cursor: {e}")
        return None, set()

def guardar_estado_cursor(cursor, processed_items):
    """Guarda el estado del cursor en archivo"""
    try:
        with open(CURSOR_FILE, 'w', encoding='utf-8') as f:
            json.dump({
                'cursor': cursor,
                'processed_items': list(processed_items),
                'timestamp': datetime.now().isoformat()
            }, f, indent=2)
    except Exception as e:
        print(f"⚠️ Error guardando cursor: {e}")

def obtener_grupos(board_id):
    """Obtiene todos los grupos del tablero"""
    query = f"""
    query {{
      boards(ids: {board_id}) {{
        groups {{
          id
          title
        }}
      }}
    }}
    """
    response = requests.post("https://api.monday.com/v2", headers=HEADERS, json={"query": query})
    data = response.json()
    if "data" not in data:
        print("❌ Error en respuesta:", data)
        raise Exception("Respuesta no contiene 'data'")
    return data["data"]["boards"][0]["groups"]

def obtener_elementos_con_paginacion(board_id, cursor=None, limit=100):
    """Obtiene elementos usando paginación cursor-based"""
    if cursor is None:
        # Primera consulta - items_page
        query = f"""
        query {{
          boards(ids: {board_id}) {{
            items_page(limit: {limit}) {{
              cursor
              items {{
                id
                name
                group {{
                  id
                  title
                }}
                column_values {{
                  id
                  value
                  text
                }}
              }}
            }}
          }}
        }}
        """
    else:
        # Consultas siguientes - next_items_page
        query = f"""
        query {{
          next_items_page(limit: {limit}, cursor: "{cursor}") {{
            cursor
            items {{
              id
              name
              group {{
                id
                title
              }}
              column_values {{
                id
                value
                text
              }}
            }}
          }}
        }}
        """
    
    response = requests.post("https://api.monday.com/v2", headers=HEADERS, json={"query": query})
    data = response.json()
    
    if "data" not in data:
        print(f"❌ Error en consulta: {data}")
        return None, []
    
    if cursor is None:
        # Respuesta de items_page
        page_data = data["data"]["boards"][0]["items_page"]
    else:
        # Respuesta de next_items_page
        page_data = data["data"]["next_items_page"]
    
    return page_data["cursor"], page_data["items"]

def obtener_url_desde_asset(asset_id):
    """Obtiene URL de un asset por su ID"""
    query = f"""
    query {{
      assets(ids: [{asset_id}]) {{
        id
        public_url
      }}
    }}
    """
    response = requests.post("https://api.monday.com/v2", headers=HEADERS, json={"query": query})
    try:
        return response.json()["data"]["assets"][0]["public_url"]
    except Exception:
        return None

def descargar_archivo(url, ruta_destino):
    """Descarga un archivo desde una URL y lo guarda EXACTAMENTE en la ruta especificada"""
    try:
        print(f"\n      🚀 INICIANDO DESCARGA")
        print(f"      🌐 URL: {url}")
        print(f"      📁 Destino: {ruta_destino}")
        
        # Asegurar que el directorio padre existe
        directorio = os.path.dirname(ruta_destino)
        if directorio and not os.path.exists(directorio):
            os.makedirs(directorio, exist_ok=True)
            print(f"      📂 Directorio creado: {directorio}")
        
        # DESCARGAR
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()
        
        # GUARDAR ARCHIVO
        with open(ruta_destino, 'wb') as f:
            total_bytes = 0
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    total_bytes += len(chunk)
        
        # VERIFICAR
        if os.path.exists(ruta_destino):
            file_size = os.path.getsize(ruta_destino)
            print(f"      ✅ ÉXITO: Archivo guardado ({file_size} bytes)")
            return True
        else:
            print(f"      ❌ ERROR: Archivo no se guardó")
            return False
            
    except Exception as e:
        print(f"      ❌ ERROR en descarga: {e}")
        return False

def procesar_item(item, grupos_dict, writer, estadisticas, processed_items):
    """Procesa un elemento individual"""
    item_id = item["id"]
    item_name = item["name"]
    group_id = item["group"]["id"]
    
    # Verificar si ya fue procesado
    if item_id in processed_items:
        print(f"⏩ Item {item_id} ya procesado, saltando...")
        return
    
    # Verificar si el grupo tiene abreviatura
    group_title = grupos_dict.get(group_id, "UNKNOWN")
    abreviatura = None
    for key, value in ABREVIATURAS.items():
        if key.upper() == group_title.upper():
            abreviatura = value
            break
    
    if not abreviatura:
        print(f"⚠️ SALTANDO item {item_name} - grupo sin abreviatura: '{group_title}'")
        processed_items.add(item_id)
        return

    print(f"\n🔍 Procesando: {item_name} (ID: {item_id})")
    print(f"   🏷️  Grupo: {group_title} -> {abreviatura}")
    
    columnas = {col["id"]: col for col in item["column_values"]}
    
    # OBTENER DATOS BÁSICOS
    estado_raw = columnas.get(STATUS_COLUMN_ID, {}).get("text", "SIN_ESTADO")
    estado_limpio = limpiar_para_carpeta(estado_raw)
    
    num_sucursal_raw = columnas.get(NUM_SUC_COLUMN_ID, {}).get("value")
    if not num_sucursal_raw:
        print(f"   ⚠️ Sin número de sucursal")
        processed_items.add(item_id)
        return

    try:
        num_sucursal = str(int(float(str(num_sucursal_raw).strip().replace('"', '')))).zfill(4)
        print(f"   📍 Sucursal: {num_sucursal}")
    except Exception as e:
        print(f"   ❌ Error procesando sucursal: {e}")
        processed_items.add(item_id)
        return

    # PROCESAR CADA COLUMNA DE ARCHIVOS
    archivos_procesados = False
    for col_id in COLUMN_IDS:
        if col_id not in columnas or not columnas[col_id].get("value"):
            continue
        
        anio = COLUMN_TO_YEAR.get(col_id, "SIN_ANIO")
        print(f"\n   📅 Procesando año: {anio}")

        try:
            archivos_info = json.loads(columnas[col_id]["value"])
            if not archivos_info.get("files"):
                continue
            
            # 🔥 CAMBIO CRÍTICO: Procesar TODOS los archivos de la columna
            total_archivos = len(archivos_info["files"])
            print(f"      📊 Total archivos en {anio}: {total_archivos}")
                
            for idx, archivo in enumerate(archivos_info["files"], 1):
                nombre_original = archivo.get("name", "sin_nombre")
                print(f"      📄 Archivo {idx}/{total_archivos}: {nombre_original}")
                
                # OBTENER URL
                url = archivo.get("url")
                if not url:
                    asset_id = archivo.get("assetId")
                    if asset_id:
                        url = obtener_url_desde_asset(asset_id)
                
                if not url:
                    print(f"      ❌ Sin URL válida para archivo {idx}")
                    estadisticas["sin_url"] += 1
                    continue

                # 🔥 CAMBIO CRÍTICO: Nombre único para cada archivo
                # Si hay múltiples archivos, añadir sufijo numérico
                if total_archivos > 1:
                    nombre_archivo_final = f"SUC_{num_sucursal}_{abreviatura}_{anio}_{idx:02d}.pdf"
                else:
                    nombre_archivo_final = f"SUC_{num_sucursal}_{abreviatura}_{anio}.pdf"
                
                ruta_final = os.path.join(DOWNLOAD_DIR, anio, estado_limpio, nombre_archivo_final)
                
                print(f"      📁 RUTA: {ruta_final}")

                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                # VERIFICAR SI YA EXISTE
                if os.path.exists(ruta_final):
                    print(f"      ⏩ Ya existe archivo {idx}")
                    writer.writerow([timestamp, group_title, item_name, num_sucursal, anio, estado_limpio, nombre_archivo_final, "YA_EXISTIA", ruta_final])
                    estadisticas["ya_existian"] += 1
                else:
                    # DESCARGAR
                    print(f"      🚀 Descargando archivo {idx}...")
                    success = descargar_archivo(url, ruta_final)
                    
                    if success:
                        print(f"      ✅ DESCARGA EXITOSA archivo {idx}")
                        writer.writerow([timestamp, group_title, item_name, num_sucursal, anio, estado_limpio, nombre_archivo_final, "DESCARGADO", ruta_final])
                        estadisticas["descargados"] += 1
                    else:
                        print(f"      ❌ DESCARGA FALLÓ archivo {idx}")
                        writer.writerow([timestamp, group_title, item_name, num_sucursal, anio, estado_limpio, nombre_archivo_final, "ERROR_DESCARGA", ruta_final])
                        estadisticas["errores"] += 1
                
                archivos_procesados = True
                        
        except Exception as e:
            print(f"   ❌ Error procesando archivos en {anio}: {e}")
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            writer.writerow([timestamp, group_title, item_name, "ERROR", anio, "ERROR", "ERROR", f"EXCEPCION: {e}", ""])
            estadisticas["errores"] += 1
    
    # Marcar como procesado
    processed_items.add(item_id)

def main():
    print(f"📋 PROCESANDO TABLERO {BOARD_ID} CON PAGINACIÓN")
    print(f"📁 Directorio destino: {DOWNLOAD_DIR}")
    
    # Crear directorios
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    os.makedirs(LOG_DIR, exist_ok=True)
    
    # Cargar estado previo
    cursor_inicial, processed_items = cargar_estado_cursor()
    processed_items = set(processed_items)  # Convertir a set para búsqueda rápida
    
    if cursor_inicial:
        print(f"🔄 REANUDANDO desde cursor guardado...")
        print(f"📊 Items ya procesados: {len(processed_items)}")
    else:
        print(f"🆕 INICIANDO desde el principio...")
    
    # Obtener grupos para mapeo
    grupos = obtener_grupos(BOARD_ID)
    grupos_dict = {g["id"]: g["title"].strip() for g in grupos}
    
    # Configurar log - 🔥 CAMBIO CRÍTICO: Usar append para no sobrescribir
    fecha_actual = datetime.now().strftime("%Y-%m-%d_%H-%M")
    nombre_log = os.path.join(LOG_DIR, f"log_descargas_{fecha_actual}.csv")
    
    # Verificar si el log ya existe para decidir si escribir headers
    log_existe = os.path.exists(nombre_log)
    
    estadisticas = {"descargados": 0, "ya_existian": 0, "sin_url": 0, "errores": 0}
    cursor_actual = cursor_inicial
    
    # 🔥 CAMBIO CRÍTICO: Usar append ("a") en lugar de write ("w")
    with open(nombre_log, mode="a", newline="", encoding="utf-8") as log_file:
        writer = csv.writer(log_file)
        
        # Solo escribir headers si el archivo es nuevo
        if not log_existe:
            writer.writerow(["timestamp", "grupo", "elemento", "sucursal", "año", "estado", "archivo_final", "estatus", "ruta_completa"])
            print(f"📝 Nuevo archivo de log creado: {nombre_log}")
        else:
            print(f"📝 Continuando log existente: {nombre_log}")
        
        pagina = 1
        items_procesados_en_sesion = 0
        
        while True:
            print(f"\n{'='*60}")
            print(f"📄 PÁGINA {pagina}")
            print(f"{'='*60}")
            
            try:
                # Obtener página actual
                nuevo_cursor, items = obtener_elementos_con_paginacion(BOARD_ID, cursor_actual, limit=100)
                
                if not items:
                    print("🏁 No hay más elementos, finalizando...")
                    break
                
                print(f"📊 Elementos en esta página: {len(items)}")
                
                # Procesar cada item
                for item in items:
                    procesar_item(item, grupos_dict, writer, estadisticas, processed_items)
                    items_procesados_en_sesion += 1
                    
                    # Guardar progreso cada 10 items
                    if items_procesados_en_sesion % 10 == 0:
                        guardar_estado_cursor(nuevo_cursor, processed_items)
                        print(f"💾 Progreso guardado ({items_procesados_en_sesion} items en esta sesión)")
                
                # Actualizar cursor para siguiente página
                cursor_actual = nuevo_cursor
                pagina += 1
                
                # Guardar progreso al final de cada página
                guardar_estado_cursor(cursor_actual, processed_items)
                
                # Si no hay nuevo cursor, hemos terminado
                if not nuevo_cursor:
                    print("🏁 Cursor vacío, hemos llegado al final...")
                    break
                    
            except Exception as e:
                print(f"❌ Error en página {pagina}: {e}")
                break
    
    # Limpiar archivo de cursor al terminar exitosamente
    if os.path.exists(CURSOR_FILE):
        os.remove(CURSOR_FILE)
        print("🧹 Estado de cursor limpiado")
    
    # RESUMEN FINAL
    print(f"\n{'='*60}")
    print(f"📊 RESUMEN FINAL DE EJECUCIÓN")
    print(f"{'='*60}")
    print(f"✅ Descargados:     {estadisticas['descargados']}")
    print(f"⏩ Ya existían:     {estadisticas['ya_existian']}")
    print(f"🚫 Sin URL:         {estadisticas['sin_url']}")
    print(f"❌ Errores:         {estadisticas['errores']}")
    print(f"📄 Páginas procesadas: {pagina - 1}")
    print(f"📊 Items en sesión: {items_procesados_en_sesion}")
    print(f"📊 Items totales procesados: {len(processed_items)}")
    print(f"📜 Log guardado:    {nombre_log}")
    print(f"📁 Directorio:      {DOWNLOAD_DIR}")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()