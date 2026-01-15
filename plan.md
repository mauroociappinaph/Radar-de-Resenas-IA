# Plan de Implementación - Mejoras para Radar de Reseñas IA

## Resumen Ejecutivo
Este plan detalla la implementación de 5 mejoras clave para el sistema "Radar de Reseñas IA":
- Paralelización con asyncio
- Análisis de sentimiento avanzado con NLP
- Sistema de clustering con K-means
- Integración postgres-mcp-server
- Integración elasticsearch-mcp-server

**Duración estimada:** 4-6 semanas
**Riesgos:** Dependencias de hardware para NLP, compatibilidad de APIs
**Beneficios:** Reducción de tiempo de procesamiento en 60%, aumento de precisión en análisis en 40%

## Prerrequisitos
- Python 3.8+
- GPU recomendada para modelos NLP (opcional pero recomendado)
- Credenciales válidas para Supabase, Exa, Firecrawl
- Acceso a repositorio GitHub

## Fase 1: Paralelización con Asyncio
### Objetivos
Convertir operaciones secuenciales a asíncronas para procesar múltiples leads simultáneamente.

### Tareas
1. **Actualizar requirements.txt**
   - Agregar: `aiohttp==3.9.1`, `asyncio`, `aiosmtplib` (para emails asíncronos)

2. **Modificar enrich.py**
   - Convertir `fetch_review_context()` a función async
   - Usar `aiohttp` para requests asíncronas
   - Implementar semáforos para rate limiting de APIs

3. **Modificar audit_agent.py**
   - Hacer `run_ai_audit()` async
   - Procesar múltiples leads concurrentemente con `asyncio.gather()`

4. **Actualizar main.py**
   - Cambiar pipeline a async
   - Agregar configuración de concurrencia (max_workers)

### Consideraciones Técnicas
- Manejar límites de rate de Exa/Firecrawl APIs
- Implementar retry logic con backoff exponencial
- Mantener compatibilidad con código existente

## Fase 2: Análisis de Sentimiento Avanzado
### Objetivos
Usar modelos NLP para analizar reseñas con mayor precisión.

### Tareas
1. **Actualizar requirements.txt**
   - Agregar: `transformers==4.36.0`, `torch==2.1.0`, `vaderSentiment==3.3.2`

2. **Crear sentiment_analyzer.py**
   - Implementar clase SentimentAnalyzer
   - Usar BERT (bert-base-multilingual-cased-sentiment) o VADER
   - Método para analizar texto y retornar scores

3. **Modificar enrich.py**
   - Integrar sentiment analyzer en `enrich_leads()`
   - Agregar campos de sentimiento al contexto

4. **Actualizar models.py**
   - Agregar campos: `sentiment_score`, `sentiment_label`, `key_emotions`

### Consideraciones Técnicas
- Modelo BERT requiere ~1GB RAM, considerar CPU fallback
- Cache de resultados para evitar re-análisis
- Manejar idiomas múltiples (español, inglés)

## Fase 3: Sistema de Clustering
### Objetivos
Agrupar leads similares para campañas segmentadas.

### Tareas
1. **Actualizar requirements.txt**
   - Agregar: `scikit-learn==1.3.0`, `pandas==2.1.0`

2. **Crear clustering.py**
   - Implementar ClusteringEngine con K-means
   - Features: nicho (one-hot), ubicación (coordenadas), rating, sentiment_score
   - Método para asignar cluster_id a leads

3. **Modificar pipeline**
   - Ejecutar clustering después del enriquecimiento
   - Almacenar cluster_id en base de datos

4. **Actualizar models.py**
   - Agregar campo `cluster_id`

### Consideraciones Técnicas
- Determinar número óptimo de clusters (método elbow)
- Re-entrenar modelo periódicamente con nuevos datos
- Almacenar centroides para predicción futura

## Fase 4: Integración postgres-mcp-server
### Objetivos
Mejorar gestión de base de datos Supabase con MCP.

### Tareas
1. **Configurar MCP**
   - Agregar postgres-mcp-server a mcp_config.json
   - Configurar conexión a Supabase PostgreSQL

2. **Crear database_manager.py**
   - Funciones para backups automáticos
   - Consultas optimizadas usando MCP
   - Monitoreo de performance

3. **Integrar en pipeline**
   - Usar MCP para queries complejas
   - Automatizar backups diarios

### Consideraciones Técnicas
- Configurar credenciales seguras
- Manejar timeouts de conexión
- Implementar rollback en caso de errores

## Fase 5: Integración elasticsearch-mcp-server
### Objetivos
Implementar búsqueda semántica en reseñas y datos.

### Tareas
1. **Configurar MCP**
   - Agregar elasticsearch-mcp-server a mcp_config.json
   - Configurar cluster Elasticsearch

2. **Modificar vector_service.py**
   - Usar Elasticsearch en lugar de Pinecone
   - Implementar indexación de review_context
   - Búsqueda semántica y full-text

3. **Crear search_indexer.py**
   - Indexar leads existentes
   - Mantener índice actualizado automáticamente

### Consideraciones Técnicas
- Configurar mappings apropiados para texto español
- Implementar búsqueda híbrida (semántica + keyword)
- Manejar escalabilidad del índice

## Cronograma
- **Semana 1:** Fase 1 (Paralelización)
- **Semana 2:** Fase 2 (Sentimiento) + Fase 3 (Clustering)
- **Semana 3:** Fase 4 (PostgreSQL MCP)
- **Semana 4:** Fase 5 (Elasticsearch MCP)
- **Semana 5-6:** Testing, optimización y documentación

## Riesgos y Mitigaciones
- **Riesgo:** Dependencia de GPU para NLP
  - **Mitigación:** Implementar fallback a CPU con VADER

- **Riesgo:** Cambios incompatibles en APIs
  - **Mitigación:** Mantener versiones antiguas como fallback

- **Riesgo:** Sobrecarga de base de datos
  - **Mitigación:** Implementar rate limiting y optimización de queries

## Métricas de Éxito
- Reducción de tiempo de procesamiento >50%
- Aumento de precisión en clasificación de emails >30%
- Disponibilidad del sistema >99%
- Reducción de costos de API >20%

## Próximos Pasos
1. Implementar fase por fase con tests
2. Merge a main después de validación
