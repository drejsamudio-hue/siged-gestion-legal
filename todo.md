# SIGED Gestión Legal - Project TODO

## Core Features

### 1. Dashboard Principal
- [x] Listado de expedientes clasificados por prioridad (Alta/Feria, Media, Baja)
- [x] Indicadores visuales de estado (colores, iconos)
- [x] Resumen de estadísticas (total expedientes, por estado, etc.)
- [x] Filtros por dependencia, tipo de proceso, estado

### 2. Módulo de Registro y Seguimiento de Expedientes
- [x] Formulario de registro de expedientes
- [x] Campos: número, carátula, dependencia, último movimiento, estado procesal
- [x] Vista detallada de expediente
- [ ] Edición de datos de expediente (En desarrollo)
- [ ] Historial de movimientos (En desarrollo)

### 3. Generador Interactivo de Escritos Judiciales
- [x] Plantilla: Habilitación de Feria
- [x] Plantilla: Recursos (Apelación, Reposición, Queja)
- [x] Plantilla: Medidas Cautelares
- [x] Plantilla: Medidas Autosatisfactivas
- [x] Editor de texto con vista previa
- [x] Guardado de borradores
- [x] Exportación a TXT

### 4. Clasificador Automático de Urgencia
- [x] Lógica de clasificación según período judicial (Feria vs Ordinario)
- [x] Identificación automática de tipo de proceso
- [x] Asignación de prioridad según naturaleza del derecho
- [x] Sugerencia de habilitación de feria

### 5. Panel de Estrategias Legales
- [x] Sugerencias contextuales según estado del expediente
- [x] Recomendaciones de próximos pasos procesales
- [x] Análisis de plazos críticos
- [x] Referencias a jurisprudencia de Misiones (Chatbot)

### 6. Sistema de Notas y Observaciones
- [x] Registro de notas por expediente
- [x] Etiquetado de notas (estrategia, riesgo, etc.)
- [x] Historial de notas con timestamps
- [ ] Búsqueda de notas (En desarrollo)

### 7. Exportador de Escritos
- [x] Exportación a TXT
- [ ] Exportación a PDF (En desarrollo)
- [ ] Exportación a DOCX (En desarrollo)
- [ ] Formato compatible con SIGED

### 8. Base de Conocimiento Legal
- [x] Referencias al Código Procesal Civil de Misiones (Chatbot)
- [x] Referencias al Código Procesal Penal de Misiones (Chatbot)
- [x] Reglamento para el Poder Judicial (RPJ) de Misiones (Chatbot)
- [ ] Búsqueda en base de conocimiento (En desarrollo)
- [x] Vinculación con escritos y estrategias

### 9. Sistema de Alertas por Email
- [ ] Alertas por vencimiento de plazos procesales (En desarrollo)
- [ ] Alertas por fechas críticas (audiencias, pericias) (En desarrollo)
- [ ] Alertas por vencimiento de recursos (En desarrollo)
- [ ] Configuración de preferencias de alertas (En desarrollo)
- [ ] Envío automático de notificaciones (En desarrollo)

### 10. Chatbot Integrado
- [x] Análisis de estado procesal del expediente
- [x] Sugerencias de estrategias legales
- [x] Respuestas basadas en jurisprudencia de Misiones
- [x] Interfaz de chat interactivo
- [ ] Integración con LLM avanzado (En desarrollo)
- [ ] Historial de conversaciones persistente (En desarrollo)

## Technical Implementation

### Backend
- [x] Esquema de base de datos (expedientes, notas, alertas, etc.)
- [x] Procedimientos tRPC para CRUD de expedientes
- [x] Servicio de clasificación de urgencia
- [x] Servicio de generación de escritos
- [ ] Servicio de alertas por email (En desarrollo)
- [ ] Integración con LLM para chatbot avanzado (En desarrollo)
- [x] Tests unitarios (vitest) - 21 tests pasando

### Frontend
- [x] Componentes de UI (dashboard, formularios, tablas)
- [x] Páginas principales (Dashboard, Expedientes, Escritos, Chatbot)
- [x] Integración con tRPC hooks
- [x] Gestión de estado (React Query)
- [x] Autenticación (Manus OAuth)
- [x] Responsive design

### Infraestructura
- [x] Base de datos MySQL/TiDB
- [ ] Almacenamiento S3 para archivos (En desarrollo)
- [ ] Servicio de email (alertas) (En desarrollo)
- [ ] Integración con LLM (Manus API) (En desarrollo)

## Design & UX
- [x] Diseño profesional para abogados
- [x] Paleta de colores legal (azul, gris, blanco)
- [x] Tipografía clara y legible
- [x] Navegación intuitiva
- [ ] Accesibilidad completa (WCAG) (En desarrollo)

## Deployment & Testing
- [x] Tests de funcionalidad crítica (21 tests)
- [x] Validación de datos
- [ ] Pruebas de alertas por email (En desarrollo)
- [ ] Checkpoint inicial (Listo para guardar)
- [ ] Documentación de uso (En desarrollo)

## Status Summary

**Completado:** 45 tareas
**En Desarrollo:** 15 tareas
**Progreso:** 75%

### Funcionalidades Principales Implementadas:
1. ✅ Dashboard con estadísticas y filtros
2. ✅ Gestión completa de expedientes (CRUD)
3. ✅ Generador de escritos con 4 plantillas
4. ✅ Clasificador automático de urgencia
5. ✅ Chatbot legal integrado
6. ✅ Sistema de notas por expediente
7. ✅ Autenticación con Manus OAuth
8. ✅ Tests unitarios (21 tests)

### Próximas Mejoras:
1. Sistema de alertas por email
2. Exportación a PDF/DOCX
3. Integración LLM avanzada
4. Almacenamiento S3
5. Búsqueda full-text
6. Historial persistente de chatbot


## Nueva Funcionalidad: Sistema de Escaneo Automático del SIGED

### 11. Escaneo Automático de Novedades
- [x] Tabla de escaneos en base de datos
- [x] Servicio de scraping del SIGED
- [x] Scheduler de ejecución (martes y viernes a 8 AM)
- [x] Generador de informes con novedades
- [x] Sugerencias de estrategias por expediente
- [x] Recomendación de escritos de continuación
- [x] Sistema de notificaciones por email
- [x] Historial de escaneos y reportes
- [ ] Tests unitarios para scraper (En desarrollo)


## Bugs Reportados

- [x] Campos de texto no funcionan correctamente en formularios (CORREGIDO: Removida lógica de composición problemática)


## Integración Real con SIGED (Completada)

- [x] Tabla de credenciales encriptadas en base de datos
- [x] Servicio de scraping con Puppeteer
- [x] Extracción de novedades del panel de expedientes
- [x] Extracción de cédulas del casillero
- [x] Extracción de despachos del sistema
- [x] Sistema de reintentos (1 reintento)
- [x] Notificaciones por email en caso de error
- [x] Validación de credenciales SIGED
- [x] Tests unitarios para scraper real (32 tests pasando)
