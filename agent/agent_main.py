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
    """
    Detecta casos MUY SIMPLES y ejecuta búsqueda directa.
    Para consultas complejas, retorna None y deja que el LLM decida.
    """
    user_input_lower = user_input.lower()
    
    # Palabras a excluir (no son búsquedas de productos)
    exclude_keywords = [
        'hola', 'hello', 'hi', 'hey', 'buenas', 'buenos', 'buena', 'saludos',
        'qué', 'que', 'cómo', 'como', 'cuándo', 'cuando', 'dónde', 'donde', 
        'por qué', 'porque', 'quién', 'quien', 'cuál', 'cual',
        'ayuda', 'help', 'gracias', 'thanks', 'ok', 'vale', 'si', 'no',
        'start', 'comenzar', 'empezar'
    ]
    
    # Detectar si el input parece un código de producto directamente (solo el código, nada más)
    code_patterns = [
        r'^\s*([A-Z]+[_-]\d+)\s*$',      # Solo FURN_8888
        r'^\s*([A-Z]+\d+[_-]\d+)\s*$',   # Solo ABC123_456
    ]
    looks_like_code = False
    extracted_code = None
    for pattern in code_patterns:
        match = re.match(pattern, user_input.upper())
        if match:
            looks_like_code = True
            extracted_code = match.group(1)
            break
    
    # Detectar frases muy cortas (1-3 palabras) que NO son saludos/preguntas
    is_excluded = any(excl in user_input_lower for excl in exclude_keywords)
    is_question = '?' in user_input
    word_count = len(user_input.split())
    
    is_very_short_phrase = (
        word_count <= 3 and 
        not is_excluded and 
        not is_question and 
        not user_input.startswith('/')
    )
    
    # SOLO activar detección automática para casos EXTREMADAMENTE SIMPLES:
    # 1. Código directo: "FURN_8888"
    # 2. Frase muy corta: "Drawer", "Office Lamp", "silla"
    if looks_like_code:
        # Caso 1: Código directo
        logger.info(f"Búsqueda automática (código): '{extracted_code}'")
        return execute_tool_call("odoo_search_products", query=extracted_code)
    
    elif is_very_short_phrase:
        # Caso 2: Frase muy corta sin contexto adicional
        query = user_input.strip()
        logger.info(f"Búsqueda automática (frase corta): '{query}'")
        return execute_tool_call("odoo_search_products", query=query)
    
    # Para TODO lo demás (consultas con contexto, preguntas, referencias, etc.)
    # retornar None y dejar que el LLM decida la query de búsqueda
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
