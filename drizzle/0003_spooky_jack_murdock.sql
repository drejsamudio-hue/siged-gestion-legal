CREATE TABLE `siged_credentials` (
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
	CONSTRAINT `siged_credentials_id` PRIMARY KEY(`id`)
);
--> statement-breakpoint
CREATE TABLE `siged_notificaciones` (
	`id` int AUTO_INCREMENT NOT NULL,
	`userId` int NOT NULL,
	`expedienteId` int,
	`tipo` varchar(50) NOT NULL,
	`titulo` text NOT NULL,
	`contenido` text,
	`fechaNotificacion` timestamp,
	`leida` int NOT NULL DEFAULT 0,
	`urlSiged` text,
	`createdAt` timestamp NOT NULL DEFAULT (now()),
	`updatedAt` timestamp NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
	CONSTRAINT `siged_notificaciones_id` PRIMARY KEY(`id`)
);
