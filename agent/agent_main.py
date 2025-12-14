import os
import logging
import re
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
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


def execute_tool_call(tool_name: str, query: str = None, product_id: int = None, limit: int = 50) -> str:
    """Ejecuta una herramienta de Odoo"""
    if tool_name not in tools_dict:
        return f"Error: Herramienta '{tool_name}' no encontrada"
    
    tool = tools_dict[tool_name]
    
    try:
        if tool_name == "odoo_search_products":
            result = tool._run(query=query, limit=limit)
        elif tool_name == "odoo_get_product_info":
            result = tool._run(product_id=product_id)
        else:
            result = "Error: Herramienta no soportada"
        
        return result
    except Exception as e:
        logger.error(f"Error ejecutando herramienta {tool_name}: {e}")
        return f"Error ejecutando la búsqueda: {str(e)}"


def detect_and_execute_tools(user_input: str) -> str:
    """Detecta si se necesita usar herramientas y las ejecuta directamente"""
    user_input_lower = user_input.lower()
    
    # Detectar búsqueda de productos
    product_keywords = ['producto', 'productos', 'articulo', 'articulos', 'item', 'items', 'inventario', 'stock']
    search_keywords = ['busca', 'buscar', 'encuentra', 'encontrar', 'muestra', 'mostrar', 'dame', 'lista', 'listar', 'detalle', 'detalles', 'info', 'información', 'informacion']
    reference_keywords = ['referencia', 'ref', 'código', 'codigo', 'barcode', 'sku']
    
    # Palabras a excluir (no son búsquedas de productos)
    exclude_keywords = [
        'hola', 'hello', 'hi', 'hey', 'buenas', 'buenos', 'buena', 'saludos',
        'qué', 'que', 'cómo', 'como', 'cuándo', 'cuando', 'dónde', 'donde', 
        'por qué', 'porque', 'quién', 'quien', 'cuál', 'cual',
        'ayuda', 'help', 'gracias', 'thanks', 'ok', 'vale', 'si', 'no',
        'start', 'comenzar', 'empezar'
    ]
    
    is_product_query = any(kw in user_input_lower for kw in product_keywords)
    is_search_query = any(kw in user_input_lower for kw in search_keywords)
    is_reference_query = any(kw in user_input_lower for kw in reference_keywords)
    
    # Detectar si hay comillas (posible búsqueda directa)
    has_quotes = bool(re.search(r"['\"]([^'\"]+)['\"]", user_input))
    
    # Detectar si el input parece un código de producto directamente
    code_patterns = [
        r'^\s*([A-Z]+[_-]\d+)\s*$',      # Solo FURN_8888
        r'^\s*([A-Z]+\d+[_-]\d+)\s*$',   # Solo ABC123_456
    ]
    looks_like_code = any(re.match(pattern, user_input.upper()) for pattern in code_patterns)
    
    # Detectar frases cortas que NO son saludos/preguntas (posible nombre de producto)
    is_excluded = any(excl in user_input_lower for excl in exclude_keywords)
    is_question = user_input_lower.strip().startswith('¿') or '?' in user_input
    word_count = len(user_input.split())
    
    # Es una frase corta potencial de búsqueda si:
    # - Tiene 1-3 palabras
    # - No contiene palabras excluidas
    # - No es una pregunta
    # - No tiene comandos (/)
    is_short_phrase = (word_count <= 3 and 
                      not is_excluded and 
                      not is_question and 
                      not user_input.startswith('/'))
    
    # CASO 1: Búsqueda automática directa
    if is_reference_query or (is_product_query and is_search_query) or has_quotes or looks_like_code or is_short_phrase:
        query = None
        
        # 1. Intentar extraer texto entre comillas
        match = re.search(r"['\"]([^'\"]+)['\"]", user_input)
        if match:
            extracted = match.group(1)
            
            # Buscar código de producto dentro (debe contener números Y guiones/guiones bajos)
            # Ejemplos válidos: FURN_8888, OL-001, ABC-123
            code_patterns = [
                r'\b([A-Z]+[_-]\d+)\b',      # FURN_8888, OL_123
                r'\b([A-Z]+\d+[_-]\d+)\b',   # ABC123_456
                r'\b([A-Z]+[_-]\d+[_-]\d+)\b'  # ABC_123_456
            ]
            
            for pattern in code_patterns:
                code_match = re.search(pattern, extracted.upper())
                if code_match:
                    query = code_match.group(1)
                    break
            
            # Si no hay código, usar el texto completo limpio
            if not query:
                cleaned = extracted.lower()
                keywords_to_remove = ['referencia', 'interna', 'ref', 'código', 'codigo', 'barcode', 'sku', ':', 'de', 'el', 'la']
                for kw in keywords_to_remove:
                    cleaned = cleaned.replace(kw, ' ')
                query = ' '.join(cleaned.split()).strip()
        
        # 2. Intentar extraer códigos/referencias sin comillas
        if not query:
            # Si el input completo parece un código, usarlo directamente
            for pattern in code_patterns:
                code_match = re.match(pattern, user_input.upper())
                if code_match:
                    query = code_match.group(1)
                    break
            
            # Si no, buscar código dentro del input
            if not query:
                search_patterns = [
                    r'\b([A-Z]+[_-]\d+)\b',      # FURN_8888, OL-001
                    r'\b([A-Z]+\d+[_-]\d+)\b',   # ABC123_456
                ]
                
                for pattern in search_patterns:
                    code_match = re.search(pattern, user_input.upper())
                    if code_match:
                        query = code_match.group(1)
                        break
        
        # 3. Extraer después de palabras clave específicas
        if not query:
            patterns = [
                r'referencia\s+interna[:\s]+(\S+)',  # "referencia interna: XXX"
                r'referencia[:\s]+(\S+)',             # "referencia: XXX"
                r'ref[:\s]+(\S+)',                    # "ref: XXX"
                r'código[:\s]+(\S+)',                 # "código: XXX"
                r'codigo[:\s]+(\S+)',                 # "codigo: XXX"
                r'barcode[:\s]+(\S+)',                # "barcode: XXX"
                r'sku[:\s]+(\S+)'                     # "sku: XXX"
            ]
            for pattern in patterns:
                match = re.search(pattern, user_input_lower)
                if match:
                    query = match.group(1).strip('.,;:')
                    break
        
        # 4. Limpieza inteligente del texto
        if not query:
            cleaned = user_input_lower
            all_keywords = search_keywords + product_keywords + reference_keywords
            all_keywords.extend(['con', 'el', 'la', 'los', 'las', 'de', 'del', 'en', 'un', 'una', 'interna', 'interno', ':'])
            
            for keyword in all_keywords:
                cleaned = cleaned.replace(keyword, ' ')
            
            query = ' '.join(cleaned.split()).strip()
        
        # Si hay query válido, ejecutar búsqueda
        if query and query.strip():
            logger.info(f"Búsqueda de productos: '{query}'")
            result = execute_tool_call("odoo_search_products", query=query)
            return result
    
    # Si no se detecta un caso específico, retornar None para usar el LLM
    return None

# Crear el agente conversacional
if tools:
    # Con herramientas de Odoo
    system_prompt = """Eres un asistente inteligente con acceso al sistema Odoo.

**TU MISIÓN:**
Ayudar a usuarios a encontrar información de productos en Odoo de forma natural y conversacional.

**CUÁNDO USAR LAS HERRAMIENTAS:**
- Cuando el usuario mencione o pregunte sobre un producto específico
- Cuando el usuario quiera información de inventario, precios, stock
- Cuando detectes que la pregunta requiere datos reales de Odoo

**HERRAMIENTAS DISPONIBLES:**
- odoo_search_products: Busca productos por nombre, referencia o código
- odoo_get_product_info: Obtiene detalles de un producto por su ID

**CÓMO RESPONDER:**
1. Si la pregunta es sobre productos → USA las herramientas para buscar en Odoo
2. Presenta los resultados de forma clara y amigable
3. Si no encuentras resultados → Explica de forma útil
4. Para saludos o preguntas generales → Responde normalmente sin usar herramientas

**IMPORTANTE:**
- NO inventes información de productos
- NO digas "voy a buscar" o "déjame consultar"
- SÉ directo pero amigable
- USA las herramientas cuando tengas dudas sobre productos

Responde de forma natural y profesional."""

    # Vincular herramientas al modelo
    model_with_tools = model.bind_tools(tools)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "{input}")
    ])
    
    # Cadena con modelo y herramientas
    chain = prompt | model_with_tools | StrOutputParser()
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
    try:
        # Si hay herramientas de Odoo, intentar ejecutarlas directamente (detección automática)
        if tools:
            tool_result = detect_and_execute_tools(user_input)
            if tool_result:
                return tool_result
        
        # Si no se ejecutó ninguna herramienta automáticamente, usar el LLM con herramientas
        if tools:
            # Preparar mensajes para el LLM
            messages = [
                ("system", """Eres un asistente inteligente con acceso al sistema Odoo.

**TU MISIÓN:**
Ayudar a usuarios a encontrar información de productos en Odoo de forma natural y conversacional.

**CUÁNDO USAR LAS HERRAMIENTAS:**
- Cuando el usuario mencione o pregunte sobre un producto específico
- Cuando el usuario quiera información de inventario, precios, stock
- Cuando detectes que la pregunta requiere datos reales de Odoo

**HERRAMIENTAS DISPONIBLES:**
- odoo_search_products: Busca productos por nombre, referencia o código
- odoo_get_product_info: Obtiene detalles de un producto por su ID

**CÓMO RESPONDER:**
1. Si la pregunta es sobre productos → USA las herramientas para buscar en Odoo
2. Presenta los resultados de forma clara y amigable
3. Si no encuentras resultados → Explica de forma útil
4. Para saludos o preguntas generales → Responde normalmente sin usar herramientas

**IMPORTANTE:**
- NO inventes información de productos
- NO digas "voy a buscar" o "déjame consultar"
- SÉ directo pero amigable
- USA las herramientas cuando tengas dudas sobre productos

Responde de forma natural y profesional."""),
                ("human", user_input)
            ]
            
            # Invocar el modelo con herramientas
            response = model_with_tools.invoke([
                {"role": "system", "content": messages[0][1]},
                {"role": "user", "content": user_input}
            ])
            
            # Verificar si el LLM quiere usar herramientas
            if hasattr(response, 'tool_calls') and response.tool_calls:
                tool_messages = []
                
                # Ejecutar cada tool call
                for tool_call in response.tool_calls:
                    tool_name = tool_call['name']
                    tool_args = tool_call['args']
                    
                    logger.info(f"LLM invocando herramienta: {tool_name} con args: {tool_args}")
                    
                    # Ejecutar la herramienta correspondiente
                    if tool_name == "odoo_search_products":
                        tool_result = execute_tool_call(
                            tool_name="odoo_search_products",
                            query=tool_args.get('query'),
                            limit=tool_args.get('limit', 50)
                        )
                    elif tool_name == "odoo_get_product_info":
                        tool_result = execute_tool_call(
                            tool_name="odoo_get_product_info",
                            product_id=tool_args.get('product_id')
                        )
                    else:
                        tool_result = f"Herramienta {tool_name} no soportada"
                    
                    # Agregar el resultado como mensaje de herramienta
                    tool_messages.append({
                        "role": "tool",
                        "content": tool_result,
                        "tool_call_id": tool_call['id']
                    })
                
                # Invocar el LLM nuevamente con los resultados de las herramientas
                final_response = model.invoke([
                    {"role": "system", "content": messages[0][1]},
                    {"role": "user", "content": user_input},
                    {"role": "assistant", "content": response.content or "", "tool_calls": response.tool_calls},
                    *tool_messages
                ])
                
                return final_response.content
            else:
                # No usó herramientas, retornar respuesta directa
                return response.content
        else:
            # Sin herramientas, usar cadena simple
            response = chain.invoke({"input": user_input})
            return response
        
    except Exception as e:
        logger.error(f"Error ejecutando agente: {e}", exc_info=True)
        return f"Lo siento, ocurrió un error al procesar tu solicitud: {str(e)}"
