CREATE TABLE `justi_credentials` (
	`id` int AUTO_INCREMENT NOT NULL,
	`userId` int NOT NULL,
	`username` text NOT NULL,
	`password` text NOT NULL,
	`notificationEmail` varchar(320) NOT NULL,
	`lastSuccessfulSync` timestamp,
	`lastSyncError` text,
	`isActive` int NOT NULL DEFAULT 1,
	`createdAt` timestamp NOT NULL DEFAULT (now()),
	`updatedAt` timestamp NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
	CONSTRAINT `justi_credentials_id` PRIMARY KEY(`id`)
);
--> statement-breakpoint
CREATE TABLE `justi_notificaciones` (
	`id` int AUTO_INCREMENT NOT NULL,
	`userId` int NOT NULL,
	`expedienteId` int,
	`tipo` varchar(50) NOT NULL,
	`titulo` text NOT NULL,
	`contenido` text,
	`fechaNotificacion` timestamp,
	`leida` int NOT NULL DEFAULT 0,
	`urlJusti` text,
	`createdAt` timestamp NOT NULL DEFAULT (now()),
	`updatedAt` timestamp NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
	CONSTRAINT `justi_notificaciones_id` PRIMARY KEY(`id`)
);
--> statement-breakpoint
CREATE TABLE `justi_novedades` (
	`id` int AUTO_INCREMENT NOT NULL,
	`userId` int NOT NULL,
	`numero` varchar(100) NOT NULL,
	`caratula` text,
	`dependencia` varchar(255),
	`ultimoMovimiento` text,
	`fechaMovimiento` timestamp,
	`estado` varchar(20) NOT NULL DEFAULT 'normal',
	`leida` int NOT NULL DEFAULT 0,
	`createdAt` timestamp NOT NULL DEFAULT (now()),
	`updatedAt` timestamp NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
	CONSTRAINT `justi_novedades_id` PRIMARY KEY(`id`)
);
