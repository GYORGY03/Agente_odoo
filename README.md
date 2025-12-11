# Agente Pyxel - Bot de Telegram

Bot conversacional para Telegram usando LangChain y Google Gemini.

## Características

- 🤖 Asistente conversacional inteligente con Gemini
- 💬 Integración completa con Telegram
- ⚡ Respuestas en tiempo real
- 📝 Sistema de logging
- 🔒 Manejo seguro de API keys
- 🔧 Integración con Odoo vía MCP (Model Context Protocol)

## Instalación

1. Crea un entorno virtual (opcional pero recomendado):
```bash
python3 -m venv venv
source venv/bin/activate  # En Linux/Mac
```

2. Instala las dependencias:
```bash
pip install -r requirements.txt
```

3. Configura las API keys:

   **Google Gemini:**
   - Obtén tu API key desde [Google AI Studio](https://makersuite.google.com/app/apikey)
   
   **Telegram Bot:**
   - Abre Telegram y busca [@BotFather](https://t.me/botfather)
   - Envía `/newbot` y sigue las instrucciones
   - Copia el token que te proporciona
   
   **Odoo MCP (Opcional):**
   - Si tienes un servidor MCP de Odoo, configura la ruta en `.env`
   - Habilita la integración con `ODOO_MCP_ENABLED=true`
   
   **Configura el archivo .env:**
   ```bash
   cp .env.example .env
   # Edita .env y agrega tus API keys y configuración de Odoo
   ```

## Uso

1. Ejecuta el bot:
```bash
python main.py
```

2. Abre Telegram y busca tu bot por el nombre que le diste

3. Envía `/start` para comenzar a chatear

## Comandos del Bot

- `/start` - Inicia el bot y muestra mensaje de bienvenida
- `/help` - Muestra información de ayuda

## Estructura del Proyecto

```
Agente_pyxel/
├── main.py              # Bot de Telegram
├── agent/
│   └── agent_main.py    # Lógica del agente conversacional
├── models/
│   └── gemini.py        # Configuración del modelo Gemini
├── tools/               # Herramientas MCP para Odoo
│   ├── __init__.py
│   ├── mcp_odoo_client.py      # Cliente MCP para Odoo
│   └── odoo_tools_wrapper.py   # Wrapper de herramientas LangChain
├── memory/              # Sistema de memoria (futuro)
├── requirements.txt     # Dependencias del proyecto
└── .env                 # Variables de entorno (API keys)
```

## Notas

- ⚠️ Asegúrate de tener una API key válida de Google Gemini ([obtén una aquí](https://makersuite.google.com/app/apikey))
- 🔑 Necesitas crear un bot en Telegram usando [@BotFather](https://t.me/botfather)
- 🤖 El modelo configurado es `gemini-pro`
- 📊 Los logs se muestran en consola para monitoreo
- 🔐 Nunca compartas tu `.env` o subas tus API keys a repositorios públicos
- 🔧 La integración con Odoo MCP es opcional y se activa en `.env`

## Integración con Odoo MCP

El bot puede conectarse a un servidor MCP de Odoo para acceder a datos del ERP:

### Configuración:

1. Asegúrate de tener tu servidor MCP de Odoo funcionando
2. Edita `.env` y configura:
   ```bash
   ODOO_MCP_ENABLED=true
   ODOO_MCP_SERVER_PATH=/ruta/a/tu/odoo_mcp_server.py
   ```

### Herramientas disponibles:

- **Búsqueda de Partners/Clientes**: Busca contactos y clientes en Odoo
- **Información de Partners**: Obtiene detalles completos de un cliente
- **Búsqueda de Productos**: Busca productos en el catálogo
- **Órdenes de Venta**: Consulta órdenes de venta, filtradas por cliente si es necesario

### Ejemplo de uso:

Una vez configurado, puedes hacer preguntas al bot como:
- "Busca el cliente ABC Company"
- "Muéstrame las órdenes de venta del cliente 123"
- "Busca productos que contengan 'laptop'"

## Solución de Problemas

**El bot no responde:**
- Verifica que las API keys estén correctamente configuradas en `.env`
- Revisa los logs en la consola para ver errores específicos
- Asegúrate de que el token del bot sea válido

**Error de importación:**
- Asegúrate de haber instalado todas las dependencias: `pip install -r requirements.txt`
- Verifica que estés usando el entorno virtual correcto

**Problemas con Odoo MCP:**
- Verifica que la ruta al servidor MCP sea correcta
- Asegúrate de que el servidor MCP esté funcionando
- Revisa los logs para ver errores específicos de conexión
- El bot funcionará sin Odoo si hay problemas con la conexión

## Próximas Funcionalidades

- 💾 Memoria conversacional persistente
- 🎯 Comandos adicionales de Telegram
- 📸 Soporte para imágenes
- 📊 Reportes y estadísticas de Odoo
- 🔔 Notificaciones automáticas desde Odoo
