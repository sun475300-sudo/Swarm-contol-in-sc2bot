CREATE TABLE `arena_matches` (
	`id` int AUTO_INCREMENT NOT NULL,
	`userId` int NOT NULL,
	`matchId` varchar(255),
	`opponentName` varchar(255),
	`opponentRace` enum('Terran','Protoss','Zerg'),
	`mapName` varchar(255),
	`result` enum('Win','Loss','Tie') NOT NULL,
	`ranking` int,
	`elo` int,
	`replayUrl` varchar(512),
	`createdAt` timestamp NOT NULL DEFAULT (now()),
	CONSTRAINT `arena_matches_id` PRIMARY KEY(`id`)
);
--> statement-breakpoint
CREATE TABLE `battles` (
	`id` int AUTO_INCREMENT NOT NULL,
	`sessionId` int NOT NULL,
	`battleTime` int NOT NULL,
	`location` varchar(255),
	`unitsEngaged` int,
	`unitsKilled` int,
	`unitsLost` int,
	`damageDealt` float,
	`damageTaken` float,
	`result` enum('Win','Loss','Retreat') NOT NULL,
	`createdAt` timestamp NOT NULL DEFAULT (now()),
	CONSTRAINT `battles_id` PRIMARY KEY(`id`)
);
--> statement-breakpoint
CREATE TABLE `bot_configs` (
	`id` int AUTO_INCREMENT NOT NULL,
	`userId` int NOT NULL,
	`name` varchar(255) NOT NULL,
	`strategy` enum('Aggressive','Defensive','Balanced','Economic','Rush') NOT NULL DEFAULT 'Balanced',
	`buildOrder` text,
	`isActive` boolean NOT NULL DEFAULT false,
	`description` text,
	`createdAt` timestamp NOT NULL DEFAULT (now()),
	`updatedAt` timestamp NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
	CONSTRAINT `bot_configs_id` PRIMARY KEY(`id`)
);
--> statement-breakpoint
CREATE TABLE `game_sessions` (
	`id` int AUTO_INCREMENT NOT NULL,
	`userId` int NOT NULL,
	`mapName` varchar(255) NOT NULL,
	`enemyRace` enum('Terran','Protoss','Zerg','Random') NOT NULL,
	`difficulty` varchar(50) NOT NULL,
	`result` enum('Victory','Defeat','InProgress') NOT NULL DEFAULT 'InProgress',
	`gamePhase` varchar(50),
	`duration` int,
	`finalSupply` int,
	`finalMinerals` int,
	`finalGas` int,
	`unitsKilled` int,
	`unitsLost` int,
	`createdAt` timestamp NOT NULL DEFAULT (now()),
	`updatedAt` timestamp NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
	CONSTRAINT `game_sessions_id` PRIMARY KEY(`id`)
);
--> statement-breakpoint
CREATE TABLE `training_episodes` (
	`id` int AUTO_INCREMENT NOT NULL,
	`userId` int NOT NULL,
	`episodeNumber` int NOT NULL,
	`totalReward` float NOT NULL,
	`averageReward` float,
	`winRate` float,
	`gamesPlayed` int NOT NULL,
	`learningRate` float,
	`epsilon` float,
	`loss` float,
	`notes` text,
	`createdAt` timestamp NOT NULL DEFAULT (now()),
	CONSTRAINT `training_episodes_id` PRIMARY KEY(`id`)
);
