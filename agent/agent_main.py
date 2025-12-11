import os
import logging
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain.tools import tool
from models.open_ai import model

logger = logging.getLogger(__name__)

# Herramientas del agente
tools = []
odoo_client = None

ODOO_MCP_ENABLED = os.getenv("ODOO_MCP_ENABLED", "false").lower() == "true"
ODOO_MCP_SERVER_PATH = os.getenv("ODOO_MCP_SERVER_PATH", "")

if ODOO_MCP_ENABLED and ODOO_MCP_SERVER_PATH:
    try:
        from tools.odoo_tools_wrapper import create_odoo_langchain_tools
        logger.info(f"Inicializando herramientas de Odoo MCP: {ODOO_MCP_SERVER_PATH}")
        
        odoo_client, odoo_tools = create_odoo_langchain_tools(
            server_script_path=ODOO_MCP_SERVER_PATH,
            auto_connect=True
        )
        tools.extend(odoo_tools)
        logger.info(f"Herramientas de Odoo cargadas: {len(odoo_tools)}")
        
    except Exception as e:
        logger.error(f"Error cargando herramientas de Odoo: {e}")
        logger.warning("El agente continuará sin herramientas de Odoo")

# Crear el agente conversacional
if tools:
    # Con herramientas de Odoo
    system_prompt = """Eres un asistente inteligente con acceso al sistema ERP Odoo a través de herramientas especializadas.

Cuando un usuario te pida información sobre clientes, contactos, productos, o pedidos de venta, DEBES usar las herramientas disponibles para consultarlo en Odoo.

**IMPORTANTE:** 
- Si el usuario pregunta por clientes, partners o contactos → Usa la herramienta de búsqueda de partners
- Si el usuario pide información detallada de un cliente específico → Usa la herramienta de obtener información del partner
- Si el usuario pregunta por productos → Usa la herramienta de búsqueda de productos
- Si el usuario pregunta por órdenes de venta o pedidos → Usa la herramienta de obtener órdenes de venta

**Herramientas disponibles:**
{tools_description}

**Instrucciones de uso:**
1. Cuando el usuario haga una solicitud relacionada con Odoo, identifica qué herramienta necesitas
2. Usa la herramienta apropiada para obtener la información
3. Presenta los resultados de forma clara y organizada
4. Si no encuentras resultados, informa al usuario amablemente

**Ejemplos de uso correcto:**
- Usuario: "Busca el cliente XYZ" → Usar herramienta de búsqueda de partners con query="XYZ"
- Usuario: "Muéstrame los productos de laptop" → Usar herramienta de búsqueda de productos con query="laptop"
- Usuario: "Órdenes de venta del cliente 123" → Usar herramienta de órdenes con partner_id=123

Para cualquier otra consulta no relacionada con Odoo, responde normalmente como un asistente útil.
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
    try:
        # Si hay herramientas de Odoo disponibles, intentar detectar si el usuario necesita usarlas
        if tools:
            # Palabras clave que indican que se debe usar Odoo
            odoo_keywords = [
                'cliente', 'clientes', 'partner', 'partners', 'contacto', 'contactos',
                'producto', 'productos', 'articulo', 'articulos',
                'orden', 'ordenes', 'pedido', 'pedidos', 'venta', 'ventas',
                'busca', 'buscar', 'encuentra', 'encontrar', 'muestra', 'mostrar',
                'dame', 'dime', 'información', 'informacion', 'datos', 'detalle', 'detalles'
            ]
            
            user_input_lower = user_input.lower()
            uses_odoo_keyword = any(keyword in user_input_lower for keyword in odoo_keywords)
            
            if uses_odoo_keyword:
                # Agregar instrucción explícita para usar herramientas
                enhanced_input = f"{user_input}\n\n[INSTRUCCIÓN INTERNA: Esta consulta requiere usar las herramientas de Odoo disponibles. Identifica qué herramienta usar y úsala para obtener la información solicitada.]"
                response = chain.invoke({"input": enhanced_input})
            else:
                response = chain.invoke({"input": user_input})
        else:
            response = chain.invoke({"input": user_input})
        
        return response
    except Exception as e:
        logger.error(f"Error ejecutando agente: {e}")
        return f"Lo siento, ocurrió un error al procesar tu solicitud: {str(e)}"