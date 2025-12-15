import os
import logging
import re
import asyncio
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from models.open_ai import model

logger = logging.getLogger(__name__)

# Cliente MCP de Odoo
mcp_client = None
mcp_tools_info = []

# Configuración de Odoo MCP
ODOO_MCP_ENABLED = os.getenv("ODOO_MCP_ENABLED", "false").lower() == "true"
ODOO_MCP_SERVER_PATH = os.getenv("ODOO_MCP_SERVER_PATH", "")

if ODOO_MCP_ENABLED and ODOO_MCP_SERVER_PATH:
    try:
        import httpx
        logger.info(f"Inicializando cliente MCP de Odoo: {ODOO_MCP_SERVER_PATH}")
        
        # Crear cliente HTTP simple para MCP
        class SimpleMCPClient:
            def __init__(self, server_url):
                self.server_url = server_url.rstrip('/')
                self.http_client = None
                self.session_id = None
                self._request_id = 0
                self.tools = []
            
            def _get_next_id(self):
                self._request_id += 1
                return self._request_id
            
            async def connect(self):
                """Conecta al servidor MCP"""
                if self.http_client:
                    return
                
                self.http_client = httpx.AsyncClient(timeout=30.0)
                
                # Inicializar sesión
                response = await self.http_client.post(
                    self.server_url,
                    json={
                        "jsonrpc": "2.0",
                        "id": self._get_next_id(),
                        "method": "initialize",
                        "params": {
                            "protocolVersion": "2024-11-05",
                            "capabilities": {},
                            "clientInfo": {"name": "telegram-bot", "version": "1.0"}
                        }
                    }
                )
                
                if response.status_code == 200:
                    self.session_id = response.headers.get('mcp-session-id')
                    logger.info("Cliente MCP conectado exitosamente")
                    
                    # Obtener herramientas disponibles
                    tools_resp = await self.http_client.post(
                        self.server_url,
                        json={"jsonrpc": "2.0", "id": self._get_next_id(), "method": "tools/list", "params": {}},
                        headers={"mcp-session-id": self.session_id} if self.session_id else {}
                    )
                    
                    if tools_resp.status_code == 200:
                        result = tools_resp.json()
                        if "result" in result and "tools" in result["result"]:
                            self.tools = result["result"]["tools"]
                            logger.info(f"Herramientas MCP disponibles: {len(self.tools)}")
            
            async def call_tool(self, tool_name, arguments):
                """Llama a una herramienta MCP"""
                if not self.http_client:
                    await self.connect()
                
                response = await self.http_client.post(
                    self.server_url,
                    json={
                        "jsonrpc": "2.0",
                        "id": self._get_next_id(),
                        "method": "tools/call",
                        "params": {"name": tool_name, "arguments": arguments}
                    },
                    headers={"mcp-session-id": self.session_id} if self.session_id else {}
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if "result" in result:
                        return result["result"]
                
                raise Exception(f"Error llamando herramienta: {response.status_code}")
            
            async def disconnect(self):
                """Desconecta del servidor"""
                if self.http_client:
                    await self.http_client.aclose()
                    self.http_client = None
        
        mcp_client = SimpleMCPClient(ODOO_MCP_SERVER_PATH)
        mcp_tools_info = []
        
        # Flag para indicar que el cliente debe conectarse en el primer uso
        mcp_client._needs_init = True
        
        logger.info(f"Cliente MCP configurado para: {ODOO_MCP_SERVER_PATH}")
        
    except Exception as e:
        logger.error(f"Error inicializando cliente MCP: {e}")
        logger.warning("El agente continuará sin herramientas MCP")
        mcp_client = None


async def execute_mcp_tool(tool_name: str, arguments: dict) -> str:
    """Ejecuta una herramienta del servidor MCP"""
    global mcp_tools_info
    
    if not mcp_client:
        return "Error: Cliente MCP no disponible"
    
    try:
        # Inicializar el cliente si es necesario
        if hasattr(mcp_client, '_needs_init') and mcp_client._needs_init:
            logger.info("Inicializando conexión MCP...")
            await mcp_client.connect()
            mcp_tools_info = mcp_client.tools
            mcp_client._needs_init = False
            logger.info(f"Cliente MCP inicializado con {len(mcp_tools_info)} herramientas")
        
        result = await mcp_client.call_tool(tool_name, arguments)
        
        # Extraer contenido de la respuesta MCP
        if isinstance(result, dict) and "content" in result:
            content_list = result["content"]
            if content_list and len(content_list) > 0:
                return content_list[0].get("text", str(result))
        
        return str(result)
        
    except Exception as e:
        logger.error(f"Error ejecutando herramienta MCP {tool_name}: {e}")
        return f"Error: {str(e)}"


async def detect_and_execute_tools(user_input: str) -> str:
    """Detecta casos simples y ejecuta búsqueda directa usando MCP"""
    if not mcp_client:
        return None
    
    user_input_lower = user_input.lower()
    
    # Palabras a excluir
    exclude_keywords = [
        'hola', 'hello', 'hi', 'hey', 'buenas', 'buenos', 'saludos',
        'qué', 'que', 'cómo', 'como', 'ayuda', 'help', 'gracias', 'ok'
    ]
    
    # Detectar código de producto
    code_patterns = [
        r'^\s*([A-Z]+[_-]\d+)\s*$',
        r'^\s*([A-Z]+\d+[_-]\d+)\s*$',
    ]
    
    for pattern in code_patterns:
        match = re.match(pattern, user_input.upper())
        if match:
            code = match.group(1)
            logger.info(f"Búsqueda MCP automática por código: '{code}'")
            result = await execute_mcp_tool("search_records", {
                "model": "product.product",
                "domain": [["default_code", "=", code]],
                "fields": ["name", "default_code", "list_price", "standard_price", "qty_available", "categ_id"],
                "limit": 10
            })
            return result
    
    # Detectar frases cortas
    is_excluded = any(excl in user_input_lower for excl in exclude_keywords)
    is_question = '?' in user_input
    word_count = len(user_input.split())
    
    if word_count <= 3 and not is_excluded and not is_question and not user_input.startswith('/'):
        query = user_input.strip()
        logger.info(f"Búsqueda MCP automática: '{query}'")
        result = await execute_mcp_tool("search_records", {
            "model": "product.product",
            "domain": [["name", "ilike", query]],
            "fields": ["name", "default_code", "list_price", "standard_price", "qty_available", "categ_id"],
            "limit": 10
        })
        return result
    
    return None


# Crear el agente conversacional
if mcp_client:
    # Con herramientas MCP de Odoo
    # Nota: La lista de herramientas se cargará en el primer uso
    tools_description = """
- list_models: Lista todos los modelos disponibles en Odoo
- search_records: Busca registros en un modelo con filtros
- get_record: Obtiene un registro específico por ID
- create_record: Crea un nuevo registro
- update_record: Actualiza un registro existente
- delete_record: Elimina un registro
- execute_method: Ejecuta un método de un modelo
- search_count: Cuenta registros que cumplen condiciones
- get_model_fields: Obtiene campos de un modelo
- model_info: Información sobre un modelo
- server_status: Estado del servidor Odoo
- cache_stats: Estadísticas de caché
"""
    
    system_prompt = f"""Eres un asistente inteligente con acceso al sistema ERP Odoo a través de MCP.

**HERRAMIENTAS DISPONIBLES:**
{tools_description}

**CÓMO USAR LAS HERRAMIENTAS:**
Usa la función call_mcp_tool con estos parámetros:
- tool_name: nombre de la herramienta MCP a llamar
- parameters: diccionario con los parámetros necesarios

**EJEMPLOS DE USO:**

1. Listar todos los modelos disponibles:
   call_mcp_tool(tool_name="list_models", parameters={{}})

2. Buscar productos por nombre:
   call_mcp_tool(tool_name="search_records", parameters={{
       "model": "product.product",
       "domain": [["name", "ilike", "lamp"]],
       "fields": ["name", "default_code", "list_price", "qty_available"],
       "limit": 10
   }})

3. Obtener información de un producto específico:
   call_mcp_tool(tool_name="get_record", parameters={{
       "model": "product.product",
       "record_id": 123,
       "fields": ["name", "list_price", "qty_available"]
   }})

**CUÁNDO USAR CADA HERRAMIENTA:**
- list_models: Cuando pregunten qué modelos/tablas hay disponibles
- search_records: Para buscar registros (productos, clientes, etc.)
- get_record: Para obtener detalles de un registro específico por ID
- model_info: Para ver qué campos tiene un modelo

**IMPORTANTE:**
- SIEMPRE usa las herramientas para consultar datos reales de Odoo
- NO inventes información
- Presenta los resultados de forma clara y amigable
- Si no encuentras resultados, explica de forma útil

Responde de forma natural y profesional."""

    logger.info("Agente inicializado con cliente MCP (herramientas se cargarán en primer uso)")
else:
    system_prompt = "Eres un asistente inteligente y útil. Responde de manera clara, amigable y profesional."
    logger.info("Agente inicializado sin herramientas")


async def run_agent(user_input: str) -> str:
    """Ejecuta el agente con la entrada del usuario"""
    try:
        # Si hay cliente MCP, intentar detección automática primero
        if mcp_client:
            tool_result = await detect_and_execute_tools(user_input)
            if tool_result:
                return tool_result
            
            # Si no se detectó automáticamente, analizar si necesita herramientas MCP
            # mediante el LLM pero sin bind_tools (manualmente)
            
            # Crear descripción de herramientas para el prompt
            tools_json = []
            for tool_info in mcp_tools_info:
                tools_json.append({
                    "name": tool_info["name"],
                    "description": tool_info.get("description", ""),
                    "parameters": tool_info.get("inputSchema", {})
                })
            
            # Prompt que incluye las herramientas disponibles
            enhanced_prompt = f"""{system_prompt}

Para usar una herramienta, responde EXACTAMENTE en este formato JSON:
{{
    "action": "use_tool",
    "tool_name": "nombre_herramienta",
    "parameters": {{"param1": "valor1"}}
}}

Si NO necesitas usar herramientas, responde normalmente en texto.

Herramientas disponibles (JSON):
{tools_json}"""
            
            # Primera invocación del LLM
            messages = [
                {"role": "system", "content": enhanced_prompt},
                {"role": "user", "content": user_input}
            ]
            
            response = model.invoke(messages)
            response_text = response.content
            
            # Verificar si el LLM quiere usar una herramienta
            import json
            import re
            
            # Buscar JSON en la respuesta
            json_match = re.search(r'\{[\s\S]*"action"[\s\S]*"use_tool"[\s\S]*\}', response_text)
            
            if json_match:
                try:
                    tool_request = json.loads(json_match.group())
                    tool_name = tool_request.get("tool_name")
                    parameters = tool_request.get("parameters", {})
                    
                    logger.info(f"LLM solicitó herramienta: {tool_name} con params: {parameters}")
                    
                    # Ejecutar la herramienta MCP
                    tool_result = await execute_mcp_tool(tool_name, parameters)
                    
                    # Invocar el LLM nuevamente con el resultado
                    messages.append({"role": "assistant", "content": response_text})
                    messages.append({"role": "user", "content": f"Resultado de la herramienta: {tool_result}"})
                    
                    final_response = model.invoke(messages)
                    return final_response.content
                    
                except json.JSONDecodeError:
                    logger.warning("El LLM intentó usar herramienta pero el JSON era inválido")
                    return response_text
            else:
                # No necesita herramientas, respuesta directa
                return response_text
        
        # Sin MCP, usar el LLM simple
        prompt_template = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", user_input)
        ])
        
        response = model.invoke(prompt_template.format_messages())
        return response.content
        
    except Exception as e:
        logger.error(f"Error ejecutando agente: {e}", exc_info=True)
        return f"Lo siento, ocurrió un error al procesar tu solicitud: {str(e)}"
