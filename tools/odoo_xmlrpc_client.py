import xmlrpc.client
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class OdooXMLRPCClient:
    """Cliente XML-RPC para conectarse a Odoo 17"""
    
    def __init__(self, url: str, db: str, username: str, password: str):

        self.url = url
        self.db = db
        self.username = username
        self.password = password
        self.uid = None
        self.common = None
        self.models = None
        
    def connect(self) -> bool:
        """Conecta y autentica con Odoo"""
        print(f"\n[ODOO CLIENT] Iniciando conexión...")
        print(f"[ODOO CLIENT] URL: {self.url}")
        print(f"[ODOO CLIENT] DB: {self.db}")
        print(f"[ODOO CLIENT] Username: {self.username}")
        
        try:
            # Endpoint común para autenticación
            self.common = xmlrpc.client.ServerProxy(f'{self.url}/xmlrpc/2/common')
            
            # Verificar versión del servidor
            print(f"[ODOO CLIENT] Obteniendo versión del servidor...")
            version_info = self.common.version()
            logger.info(f"Conectado a Odoo versión: {version_info.get('server_version')}")
            print(f"[ODOO CLIENT] Versión Odoo: {version_info.get('server_version')}")
            
            # Autenticar
            print(f"[ODOO CLIENT] Autenticando...")
            self.uid = self.common.authenticate(self.db, self.username, self.password, {})
            
            if not self.uid:
                logger.error("Error de autenticación. Verifica credenciales.")
                print(f"[ODOO CLIENT] ERROR: Autenticación falló (uid=False)")
                return False
            
            logger.info(f"Autenticado exitosamente. UID: {self.uid}")
            print(f"[ODOO CLIENT] ✓ Autenticación exitosa. UID: {self.uid}")
            
            # Endpoint para llamar métodos
            self.models = xmlrpc.client.ServerProxy(f'{self.url}/xmlrpc/2/object')
            print(f"[ODOO CLIENT] ✓ Cliente models configurado")
            
            return True
            
        except Exception as e:
            logger.error(f"Error conectando a Odoo: {e}")
            print(f"[ODOO CLIENT] ERROR: {e}")
            return False
    
    def search(self, model: str, domain: List = None, offset: int = 0, limit: int = 100) -> List[int]:

        if domain is None:
            domain = []
            
        try:
            ids = self.models.execute_kw(
                self.db, self.uid, self.password,
                model, 'search',
                [domain],
                {'offset': offset, 'limit': limit}
            )
            return ids
        except Exception as e:
            logger.error(f"Error buscando en {model}: {e}")
            return []
    
    def read(self, model: str, ids: List[int], fields: List[str] = None) -> List[Dict]:

        try:
            options = {}
            if fields:
                options['fields'] = fields
                
            records = self.models.execute_kw(
                self.db, self.uid, self.password,
                model, 'read',
                [ids],
                options
            )
            return records
        except Exception as e:
            logger.error(f"Error leyendo {model}: {e}")
            return []
    
    def search_read(self, model: str, domain: List = None, fields: List[str] = None, 
                    offset: int = 0, limit: int = 100) -> List[Dict]:

        if domain is None:
            domain = []
            
        try:
            options = {'offset': offset, 'limit': limit}
            if fields:
                options['fields'] = fields
                
            records = self.models.execute_kw(
                self.db, self.uid, self.password,
                model, 'search_read',
                [domain],
                options
            )
            return records
        except Exception as e:
            logger.error(f"Error en search_read {model}: {e}")
            return []
    
    def search_count(self, model: str, domain: List = None) -> int:

        if domain is None:
            domain = []
            
        try:
            count = self.models.execute_kw(
                self.db, self.uid, self.password,
                model, 'search_count',
                [domain]
            )
            return count
        except Exception as e:
            logger.error(f"Error contando {model}: {e}")
            return 0
    
    def get_products(self, query: str = None, limit: int = 50) -> List[Dict]:
        """
        Obtiene productos del inventario
        
        Args:
            query: Término de búsqueda (busca en nombre, referencia, código de barras, categoría)
            limit: Número máximo de productos
            
        Returns:
            Lista de productos con sus datos
        """
        domain = []
        
        if query:
            # Buscar en nombre, referencia interna, código de barras o categoría
            domain = [
                '|', '|', '|',
                ['name', 'ilike', query],
                ['default_code', 'ilike', query],
                ['barcode', 'ilike', query],
                ['categ_id.name', 'ilike', query]
            ]
        
        fields = [
            'name',           # Nombre del producto
            'default_code',   # Referencia interna
            'barcode',        # Código de barras
            'type',           # Tipo (product, consu, service)
            'categ_id',       # Categoría
            'list_price',     # Precio de venta
            'standard_price', # Costo
            'qty_available',  # Cantidad disponible
            'uom_id',         # Unidad de medida
            'active',         # Activo
        ]
        
        products = self.search_read('product.product', domain, fields, limit=limit)
        logger.info(f"Búsqueda: '{query}' - {len(products)} productos encontrados")
        
        return products
    
    def get_product_by_id(self, product_id: int) -> Dict:

        fields = [
            'name', 'default_code', 'barcode', 'type', 'categ_id',
            'list_price', 'standard_price', 'qty_available', 'uom_id',
            'description', 'description_sale', 'active', 'company_id'
        ]
        
        products = self.read('product.product', [product_id], fields)
        return products[0] if products else {}
    
    def get_stock_quants(self, product_id: int = None, location_id: int = None) -> List[Dict]:

        domain = []
        
        if product_id:
            domain.append(['product_id', '=', product_id])
        if location_id:
            domain.append(['location_id', '=', location_id])
            
        fields = ['product_id', 'location_id', 'quantity', 'reserved_quantity', 'lot_id']
        
        quants = self.search_read('stock.quant', domain, fields, limit=100)
        return quants
