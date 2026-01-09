CREATE TABLE `novedades_expedientes` (
	`id` int AUTO_INCREMENT NOT NULL,
	`scanId` int NOT NULL,
	`expedienteId` int NOT NULL,
	`tipoNovedad` varchar(100) NOT NULL,
	`descripcion` text,
	`estrategiaRecomendada` text,
	`escritoSugerido` varchar(100),
	`urgencia` enum('baja','media','alta','critica') DEFAULT 'media',
	`createdAt` timestamp NOT NULL DEFAULT (now()),
	CONSTRAINT `novedades_expedientes_id` PRIMARY KEY(`id`)
);
--> statement-breakpoint
CREATE TABLE `siged_scans` (
	`id` int AUTO_INCREMENT NOT NULL,
	`userId` int NOT NULL,
	`fechaScan` timestamp NOT NULL DEFAULT (now()),
	`expedientesActualizados` int DEFAULT 0,
	`novedadesEncontradas` int DEFAULT 0,
	`estado` enum('exitoso','error','pendiente') DEFAULT 'pendiente',
	`detalles` text,
	`emailEnviado` int DEFAULT 0,
	`createdAt` timestamp NOT NULL DEFAULT (now()),
	CONSTRAINT `siged_scans_id` PRIMARY KEY(`id`)
);
