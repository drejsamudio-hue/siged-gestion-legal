CREATE TABLE `alertas` (
	`id` int AUTO_INCREMENT NOT NULL,
	`expedienteId` int NOT NULL,
	`userId` int NOT NULL,
	`titulo` varchar(255) NOT NULL,
	`descripcion` text,
	`tipo` enum('vencimiento_plazo','audiencia','pericia','vencimiento_recurso','otro') NOT NULL,
	`fechaAlerta` timestamp NOT NULL,
	`enviado` boolean NOT NULL DEFAULT false,
	`fechaEnvio` timestamp,
	`createdAt` timestamp NOT NULL DEFAULT (now()),
	`updatedAt` timestamp NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
	CONSTRAINT `alertas_id` PRIMARY KEY(`id`)
);
--> statement-breakpoint
CREATE TABLE `conversaciones` (
	`id` int AUTO_INCREMENT NOT NULL,
	`expedienteId` int,
	`userId` int NOT NULL,
	`titulo` varchar(255),
	`mensajes` json,
	`createdAt` timestamp NOT NULL DEFAULT (now()),
	`updatedAt` timestamp NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
	CONSTRAINT `conversaciones_id` PRIMARY KEY(`id`)
);
--> statement-breakpoint
CREATE TABLE `escritos` (
	`id` int AUTO_INCREMENT NOT NULL,
	`expedienteId` int,
	`userId` int NOT NULL,
	`titulo` varchar(255) NOT NULL,
	`tipo` enum('habilitacion_feria','apelacion','reposicion','queja','medida_cautelar','medida_autosatisfactiva','otro') NOT NULL,
	`contenido` text NOT NULL,
	`estado` enum('borrador','completado','presentado') NOT NULL DEFAULT 'borrador',
	`fechaPresentacion` timestamp,
	`urlPDF` varchar(500),
	`urlDOCX` varchar(500),
	`createdAt` timestamp NOT NULL DEFAULT (now()),
	`updatedAt` timestamp NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
	CONSTRAINT `escritos_id` PRIMARY KEY(`id`)
);
--> statement-breakpoint
CREATE TABLE `expedientes` (
	`id` int AUTO_INCREMENT NOT NULL,
	`userId` int NOT NULL,
	`numero` varchar(50) NOT NULL,
	`caratula` text NOT NULL,
	`dependencia` varchar(255) NOT NULL,
	`tipoProc` enum('civil_comercial','laboral','familia','penal','administrativo','otro') NOT NULL,
	`estadoProcesal` enum('inicio','demanda_contestada','prueba','alegatos','sentencia','recurso','ejecucion','finalizado','otro') NOT NULL,
	`prioridad` enum('alta_feria','media','baja') NOT NULL DEFAULT 'media',
	`ultimoMovimiento` text,
	`fechaUltimoMovimiento` timestamp,
	`proximoPlazo` timestamp,
	`notas` text,
	`archivoUrl` varchar(500),
	`createdAt` timestamp NOT NULL DEFAULT (now()),
	`updatedAt` timestamp NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
	CONSTRAINT `expedientes_id` PRIMARY KEY(`id`)
);
--> statement-breakpoint
CREATE TABLE `notas` (
	`id` int AUTO_INCREMENT NOT NULL,
	`expedienteId` int NOT NULL,
	`userId` int NOT NULL,
	`contenido` text NOT NULL,
	`tipo` enum('estrategia','riesgo','oportunidad','observacion') NOT NULL DEFAULT 'observacion',
	`createdAt` timestamp NOT NULL DEFAULT (now()),
	`updatedAt` timestamp NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
	CONSTRAINT `notas_id` PRIMARY KEY(`id`)
);
--> statement-breakpoint
CREATE TABLE `referencias_legales` (
	`id` int AUTO_INCREMENT NOT NULL,
	`titulo` varchar(255) NOT NULL,
	`tipo` enum('codigo_civil','codigo_penal','codigo_procesal_civil','codigo_procesal_penal','rpj','jurisprudencia') NOT NULL,
	`articulo` varchar(50),
	`contenido` text NOT NULL,
	`fuente` varchar(255),
	`createdAt` timestamp NOT NULL DEFAULT (now()),
	CONSTRAINT `referencias_legales_id` PRIMARY KEY(`id`)
);
