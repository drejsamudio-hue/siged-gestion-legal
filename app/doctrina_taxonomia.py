"""Ramas y especialidades de doctrina. Palabras clave en minusculas y sin tildes.

Cada especialidad es una carpeta: 03_Doctrina/<rama>/<especialidad>/. Para sumar una,
agregar una entrada con las expresiones que la delatan (cuanto mas especificas, mejor).
"""

RAMAS: dict[str, dict[str, tuple[str, ...]]] = {
    "consumo": {
        "planes-de-ahorro": ("plan de ahorro", "planes de ahorro", "administradora del plan", "grupo cerrado",
                             "cuota pura", "adjudicacion", "circulo de inversores"),
        "dano-punitivo": ("dano punitivo", "52 bis", "multa civil", "sancion pecuniaria disuasiva"),
        "relacion-de-consumo": ("relacion de consumo", "consumidor", "proveedor", "24.240", "24240",
                                "clausulas abusivas", "deber de informacion", "trato digno"),
        "bancos-y-financieras": ("tarjeta de credito", "prestamo", "usura", "tasa de interes",
                                 "entidad financiera", "resumen de cuenta", "pagare"),
        "sanciones-administrativas": ("defensa del consumidor", "autoridad de aplicacion", "multa administrativa",
                                      "sumario administrativo", "descargo"),
    },
    "laboral": {
        "despido-e-indemnizaciones": ("despido", "indemnizacion por antiguedad", "preaviso", "contrato de trabajo",
                                      "20.744", "20744"),
        "tutela-sindical": ("tutela sindical", "23.551", "23551", "asociaciones sindicales", "delegado",
                            "exclusion de tutela", "actividad sindical"),
        "accidentes-y-riesgos": ("accidente de trabajo", "enfermedad profesional", "riesgos del trabajo",
                                 "24.557", "24557", "aseguradora de riesgos"),
        "discriminacion-y-trato": ("discriminacion", "trato igualitario", "acoso laboral", "mobbing",
                                   "23.592", "23592"),
        "procesal-laboral": ("procesal laboral", "proceso laboral", "codigo procesal laboral", "conciliacion laboral"),
    },
    "procesal": {
        "caducidad-de-instancia": ("caducidad de instancia", "perencion", "impulso procesal", "actos interruptivos"),
        "medidas-cautelares": ("medida cautelar", "medidas cautelares", "verosimilitud del derecho",
                               "peligro en la demora", "embargo preventivo", "autosatisfactiva",
                               "tutela anticipada"),
        "nulidades-y-recursos": ("nulidad", "recurso de apelacion", "expresion de agravios", "recurso extraordinario",
                                 "inaplicabilidad de ley"),
        "prueba": ("carga de la prueba", "prueba pericial", "prueba testimonial", "prueba documental",
                   "cargas dinamicas"),
        "ejecucion": ("juicio ejecutivo", "proceso monitorio", "ejecucion de sentencia", "ejecuciones especiales",
                      "titulo ejecutivo", "excepciones"),
        "costas-y-gratuidad": ("costas", "beneficio de litigar sin gastos", "gratuidad", "tasa de justicia"),
    },
    "honorarios": {
        "regulacion-arancelaria": ("honorarios", "regulacion de honorarios", "ley arancelaria", "arancel",
                                   "base regulatoria", "27.423", "27423"),
        "intereses-y-actualizacion": ("tasa activa", "capitalizacion de intereses", "anatocismo",
                                      "actualizacion monetaria", "deuda de valor", "intereses moratorios"),
    },
    "danos": {
        "responsabilidad-civil": ("responsabilidad civil", "factor de atribucion", "relacion de causalidad",
                                  "danos y perjuicios", "riesgo creado"),
        "dano-moral": ("dano moral", "dano extrapatrimonial", "consecuencias no patrimoniales"),
        "transito-y-seguros": ("accidente de transito", "seguro obligatorio", "citacion en garantia", "franquicia",
                               "aseguradora"),
        "cuantificacion": ("cuantificacion", "incapacidad", "lucro cesante", "perdida de chance", "formula"),
    },
    "civil-y-comercial": {
        "contratos": ("contrato", "incumplimiento contractual", "resolucion contractual", "boleto de compraventa",
                      "locacion", "compraventa"),
        "obligaciones": ("obligaciones", "imputacion de pagos", "clausula penal", "prescripcion liberatoria",
                         "cumplimiento de la obligacion"),
        "sociedades-y-titulos": ("sociedad anonima", "ley general de sociedades", "19.550", "19550", "cheque",
                                 "letra de cambio", "quiebra", "concurso preventivo"),
    },
    "familia-y-sucesiones": {
        "alimentos": ("alimentos", "cuota alimentaria", "obligacion alimentaria", "responsabilidad parental"),
        "matrimonio-y-divorcio": ("divorcio", "nulidad de matrimonio", "union convivencial", "compensacion economica",
                                  "sociedad conyugal"),
        "sucesiones": ("sucesion", "sucesorio", "herencia", "heredero", "legitima", "declaratoria de herederos",
                       "testamento"),
    },
    "reales": {
        "usucapion": ("usucapion", "prescripcion adquisitiva", "posesion veinteanal", "posesion"),
        "dominio-y-registro": ("derechos reales", "dominio", "registro de la propiedad", "escrituracion",
                               "condominio", "propiedad horizontal", "hipoteca"),
    },
    "administrativo": {
        "contencioso-administrativo": ("contencioso administrativo", "agotamiento de la via", "acto administrativo",
                                       "demanda contra el estado"),
        "empleo-publico": ("empleo publico", "agente publico", "estabilidad del empleado publico", "cesantia"),
        "responsabilidad-del-estado": ("responsabilidad del estado", "responsabilidad estatal", "falta de servicio",
                                       "expropiacion"),
    },
    "constitucional": {
        "garantias-y-amparo": ("amparo", "habeas corpus", "habeas data", "garantias constitucionales",
                               "control de constitucionalidad", "inconstitucionalidad"),
        "historia-y-teoria": ("historia constitucional", "constitucion nacional", "reforma constitucional",
                              "poder constituyente", "federalismo"),
        "derechos-humanos": ("derechos humanos", "convencion americana", "corte interamericana",
                             "control de convencionalidad", "tratados internacionales"),
    },
    "penal": {
        "parte-general": ("derecho penal", "teoria del delito", "dolo", "culpabilidad", "tipicidad",
                          "antijuridicidad"),
        "procesal-penal": ("procesal penal", "codigo procesal penal", "nulidad penal", "prision preventiva",
                           "juicio oral", "imputado"),
    },
}

RAMA_SIN_DEFINIR = ("general", "sin-especialidad")
