# SOAP - Radar de Reseñas IA

## Objetivo
Automatizar la prospección y auditoría de negocios locales (dentistas, gimnasios, etc.) para ofrecer servicios de gestión de reputación e IA.

## Flujo de Trabajo
1. **Scouting (`scout.py`):** Buscar negocios en nichos/ciudades específicas usando Exa.
2. **Enriquecimiento (`enrich.py`):** Extraer emails personales y contexto de reseñas (quejas/elogios).
3. **Análisis (`audit_agent.py`):** Generar borradores de emails hiper-personalizados usando un LLM.
4. **Visualización (`dashboard/index.html`):** Revisar los prospectos de alta calidad.
5. **Automatización:** Ejecución diaria vía GitHub Actions.
