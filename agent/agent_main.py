import os
import logging
import re
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from models.open_ai import model

logger = logging.getLogger(__name__)

# Herramientas del agente
tools = []
odoo_client = None
tools_dict = {}  # Diccionario para acceso rápido a herramientas por nombre

# Configuración de Odoo XML-RPC (conexión directa)
ODOO_XMLRPC_ENABLED = os.getenv("ODOO_XMLRPC_ENABLED", "false").lower() == "true"
ODOO_URL = os.getenv("ODOO_URL", "")
ODOO_DB = os.getenv("ODOO_DB", "")
ODOO_USERNAME = os.getenv("ODOO_USERNAME", "")
ODOO_PASSWORD = os.getenv("ODOO_PASSWORD", "")

if ODOO_XMLRPC_ENABLED and all([ODOO_URL, ODOO_DB, ODOO_USERNAME, ODOO_PASSWORD]):
    try:
        from tools.odoo_xmlrpc_tools import create_odoo_xmlrpc_tools
        logger.info(f"Inicializando herramientas de Odoo XML-RPC: {ODOO_URL}")
        
        odoo_client, odoo_tools = create_odoo_xmlrpc_tools(
            url=ODOO_URL,
            db=ODOO_DB,
            username=ODOO_USERNAME,
            password=ODOO_PASSWORD,
            auto_connect=True
        )
        tools.extend(odoo_tools)
        # Crear diccionario para acceso rápido
        tools_dict = {tool.name: tool for tool in tools}
        logger.info(f"Herramientas de Odoo cargadas: {len(odoo_tools)}")
        
    except Exception as e:
        logger.error(f"Error cargando herramientas de Odoo: {e}")
        logger.warning("El agente continuará sin herramientas de Odoo")


def execute_tool_call(tool_name: str, query: str = None, product_id: int = None, limit: int = 10) -> str:
    """Ejecuta una herramienta de Odoo"""
    print(f"\n{'='*60}")
    print(f"[DEBUG] Ejecutando herramienta: {tool_name}")
    print(f"[DEBUG] Parámetros: query={query}, product_id={product_id}, limit={limit}")
    print(f"{'='*60}\n")
    
    if tool_name not in tools_dict:
        return f"Error: Herramienta '{tool_name}' no encontrada"
    
    tool = tools_dict[tool_name]
    
    try:
        if tool_name == "odoo_search_products":
            print(f"[DEBUG] Llamando a tool._run(query='{query}', limit={limit})")
            result = tool._run(query=query, limit=limit)
            print(f"[DEBUG] Resultado obtenido: {result[:200]}..." if len(str(result)) > 200 else f"[DEBUG] Resultado obtenido: {result}")
        elif tool_name == "odoo_get_product_info":
            print(f"[DEBUG] Llamando a tool._run(product_id={product_id})")
            result = tool._run(product_id=product_id)
            print(f"[DEBUG] Resultado obtenido: {result[:200]}..." if len(str(result)) > 200 else f"[DEBUG] Resultado obtenido: {result}")
        else:
            result = "Error: Herramienta no soportada"
        
        print(f"\n{'='*60}")
        print(f"[DEBUG] Ejecución completada exitosamente")
        print(f"{'='*60}\n")
        return result
    except Exception as e:
        logger.error(f"Error ejecutando herramienta {tool_name}: {e}")
        print(f"\n[ERROR] Error ejecutando herramienta: {e}\n")
        return f"Error ejecutando la búsqueda: {str(e)}"


def detect_and_execute_tools(user_input: str) -> str:
    """Detecta si se necesita usar herramientas y las ejecuta directamente"""
    print(f"\n{'*'*60}")
    print(f"[DEBUG] Detectando herramientas para: '{user_input}'")
    print(f"{'*'*60}\n")
    
    user_input_lower = user_input.lower()
    
    # Detectar búsqueda de productos - EXPANDIDO para capturar más casos
    product_keywords = ['producto', 'productos', 'articulo', 'articulos', 'item', 'items', 'inventario', 'stock']
    search_keywords = ['busca', 'buscar', 'encuentra', 'encontrar', 'muestra', 'mostrar', 'dame', 'lista', 'listar', 'detalle', 'detalles', 'info', 'información', 'informacion']
    
    is_product_query = any(kw in user_input_lower for kw in product_keywords)
    is_search_query = any(kw in user_input_lower for kw in search_keywords)
    
    print(f"[DEBUG] ¿Es consulta de producto?: {is_product_query}")
    print(f"[DEBUG] ¿Es consulta de búsqueda?: {is_search_query}")
    
    # CASO 1: Búsqueda explícita de productos
    if is_product_query and is_search_query:
        print(f"[DEBUG] CASO 1 activado: Búsqueda explícita de productos")
        # Extraer el término de búsqueda
        match = re.search(r"['\"]([^'\"]+)['\"]", user_input)
        if match:
            query = match.group(1)
            print(f"[DEBUG] Query extraído de comillas: '{query}'")
        else:
            # Remover palabras de acción y extraer el nombre del producto
            for keyword in search_keywords + product_keywords:
                user_input_lower = user_input_lower.replace(keyword, '')
            
            # Limpiar y extraer query
            query = user_input_lower.strip()
            # Remover palabras comunes
            stop_words = ['el', 'la', 'los', 'las', 'de', 'del', 'en', 'un', 'una']
            query_words = [w for w in query.split() if w not in stop_words]
            query = ' '.join(query_words) if query_words else query
            print(f"[DEBUG] Query extraído después de limpieza: '{query}'")
        
        logger.info(f"Ejecutando búsqueda de productos: query='{query}'")
        result = execute_tool_call("odoo_search_products", query=query)
        return result
    
    # CASO 2: Mención directa de producto con nombre específico
    # Ejemplo: "Office Chair Black", "laptop dell", etc
    if 'producto' in user_input_lower or 'articulo' in user_input_lower:
        print(f"[DEBUG] CASO 2 activado: Mención directa de producto")
        # Extraer texto entre comillas si existe
        match = re.search(r"['\"]([^'\"]+)['\"]", user_input)
        if match:
            query = match.group(1)
            print(f"[DEBUG] Query extraído de comillas: '{query}'")
            logger.info(f"Ejecutando búsqueda de productos (nombre específico): query='{query}'")
            result = execute_tool_call("odoo_search_products", query=query)
            return result
        else:
            print(f"[DEBUG] No se encontró texto entre comillas en CASO 2")
    
    # Si no se detecta un caso específico, retornar None para usar el LLM
    print(f"[DEBUG] No se detectó ningún caso, pasando al LLM\n")
    return None

# Crear el agente conversacional
if tools:
    # Con herramientas de Odoo
    system_prompt = """Eres un asistente que proporciona información directa del sistema Odoo.

**REGLAS ESTRICTAS:**
1. NUNCA digas "voy a buscar", "déjame consultar", "un momento" o frases similares
2. Proporciona ÚNICAMENTE los resultados solicitados
3. Si no hay resultados, di solo "No se encontraron resultados"
4. NO expliques qué herramienta vas a usar ni tus acciones
5. Responde de forma directa y concisa

**Herramientas disponibles:**
{tools_description}

**Formato de respuesta:**
- Para búsquedas: Lista los resultados encontrados directamente
- Para información específica: Muestra los datos solicitados
- Sin resultados: "No se encontraron resultados para [término]"

Sé directo, preciso y ve al grano.
"""
    
    # Crear descripciones de herramientas
    tools_description = "\n".join([f"- {tool.name}: {tool.description}" for tool in tools])
    print("**********"+tools_description+"**********")
    system_prompt_formatted = system_prompt.format(tools_description=tools_description)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt_formatted),
        ("human", "{input}")
    ])
    
    # Cadena con modelo
    chain = prompt | model | StrOutputParser()
    logger.info(f"Agente inicializado con {len(tools)} herramientas de Odoo")
else:
    # Sin herramientas
    prompt = ChatPromptTemplate.from_messages([
        ("system", "Eres un asistente inteligente y útil. Puedes responder preguntas, proporcionar información y ayudar con diversas tareas. Responde de manera clara, amigable y profesional."),
        ("human", "{input}")
    ])
    chain = prompt | model | StrOutputParser()
    logger.info("Agente inicializado sin herramientas (modo simple)")


def run_agent(user_input: str) -> str:
    """Ejecuta el agente con la entrada del usuario"""
    print(f"\n{'#'*60}")
    print(f"[DEBUG] run_agent() llamado con entrada: '{user_input}'")
    print(f"[DEBUG] Herramientas disponibles: {len(tools)}")
    print(f"{'#'*60}\n")
    
    try:
        # Si hay herramientas de Odoo, intentar ejecutarlas directamente
        if tools:
            print(f"[DEBUG] Intentando detectar y ejecutar herramientas...")
            # Intentar detectar y ejecutar herramientas automáticamente
            tool_result = detect_and_execute_tools(user_input)
            
            if tool_result:
                # Si se ejecutó una herramienta, retornar el resultado directamente
                print(f"[DEBUG] Herramienta ejecutada, retornando resultado")
                return tool_result
            else:
                print(f"[DEBUG] No se ejecutó herramienta, usando modelo LLM")
        
        # Si no se ejecutó ninguna herramienta, usar el modelo normal
        print(f"[DEBUG] Invocando chain con modelo...")
        response = chain.invoke({"input": user_input})
        print(f"[DEBUG] Respuesta del modelo: {response[:100]}..." if len(str(response)) > 100 else f"[DEBUG] Respuesta del modelo: {response}")
        return response
        
    except Exception as e:
        logger.error(f"Error ejecutando agente: {e}")
        print(f"[ERROR] Error en run_agent: {e}")
        return f"Lo siento, ocurrió un error al procesar tu solicitud: {str(e)}"
