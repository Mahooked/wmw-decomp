# water-Lite.db (122880 bytes)
# page_size=4096 encoding=UTF-8 journal=delete freelist=0 user_version=0 app_id=0

Tables: 8   views: 0   indexes: 0   triggers: 0

## Achievements  (6 rows)

    CREATE TABLE "Achievements" ("Points" INTEGER NOT NULL , "ID" TEXT PRIMARY KEY NOT NULL UNIQUE , "Hidden" INTEGER NOT NULL DEFAULT 0, "PreEarnedDescription" TEXT NOT NULL , "EarnedDescription" TEXT NOT NULL , "Image" TEXT NOT NULL , "PercentComplete" FLOAT NOT NULL DEFAULT 0, "SortingGroup" INTEGER NOT NULL DEFAULT 0, FacebookDescription TEXT)

      Points                       INTEGER, NOT NULL
      ID                           TEXT, PRIMARY KEY, NOT NULL
      Hidden                       INTEGER, NOT NULL, DEFAULT 0
      PreEarnedDescription         TEXT, NOT NULL
      EarnedDescription            TEXT, NOT NULL
      Image                        TEXT, NOT NULL
      PercentComplete              FLOAT, NOT NULL, DEFAULT 0
      SortingGroup                 INTEGER, NOT NULL, DEFAULT 0
      FacebookDescription          TEXT

## CollectibleInfo  (6 rows)

    CREATE TABLE "CollectibleInfo" ("ID" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL UNIQUE , "Unlocked" BOOL NOT NULL DEFAULT 0, "Basename" TEXT, "HasViewed" BOOL NOT NULL DEFAULT 0)

      ID                           INTEGER, PRIMARY KEY, NOT NULL
      Unlocked                     BOOL, NOT NULL, DEFAULT 0
      Basename                     TEXT
      HasViewed                    BOOL, NOT NULL, DEFAULT 0

## HubInfo  (6 rows)

    CREATE TABLE "HubInfo" ( "ID" INTEGER PRIMARY KEY NOT NULL UNIQUE , "Storyline" INTEGER DEFAULT -1, "IAP_item_id" TEXT DEFAULT '', "Bought" BOOL DEFAULT 1, "TitleTexture" TEXT DEFAULT '', "MainTexture" TEXT DEFAULT '', "FrameTexture" TEXT DEFAULT '', "TextColor" TEXT DEFAULT '', "TextLine1" TEXT DEFAULT '', "TextLine2" TEXT DEFAULT '', "DuckCharacter" TEXT DEFAULT '', "ItemCharacter" TEXT DEFAULT '', "DuckSQL1" TEXT DEFAULT '', "DuckSQL2" TEXT DEFAULT '', "ItemSQL1" TEXT DEFAULT '', "ItemSQL2" TEXT DEFAULT '', "TextButton" TEXT DEFAULT '', "AlertText" TEXT DEFAULT '' , "Unlocked" BOOL DEFAULT 0, DisplayOrder INTEGER NOT NULL DEFAULT 0, DuckyCounterTexture TEXT NOT NULL DEFAULT "")

      ID                           INTEGER, PRIMARY KEY, NOT NULL
      Storyline                    INTEGER, DEFAULT -1
      IAP_item_id                  TEXT, DEFAULT ''
      Bought                       BOOL, DEFAULT 1
      TitleTexture                 TEXT, DEFAULT ''
      MainTexture                  TEXT, DEFAULT ''
      FrameTexture                 TEXT, DEFAULT ''
      TextColor                    TEXT, DEFAULT ''
      TextLine1                    TEXT, DEFAULT ''
      TextLine2                    TEXT, DEFAULT ''
      DuckCharacter                TEXT, DEFAULT ''
      ItemCharacter                TEXT, DEFAULT ''
      DuckSQL1                     TEXT, DEFAULT ''
      DuckSQL2                     TEXT, DEFAULT ''
      ItemSQL1                     TEXT, DEFAULT ''
      ItemSQL2                     TEXT, DEFAULT ''
      TextButton                   TEXT, DEFAULT ''
      AlertText                    TEXT, DEFAULT ''
      Unlocked                     BOOL, DEFAULT 0
      DisplayOrder                 INTEGER, NOT NULL, DEFAULT 0
      DuckyCounterTexture          TEXT, NOT NULL, DEFAULT ""

## LevelInfo  (644 rows)

    CREATE TABLE "LevelInfo" ("ID" INTEGER PRIMARY KEY NOT NULL ,"Name" TEXT NOT NULL ,"Filename" TEXT NOT NULL ,"Stars" INTEGER NOT NULL DEFAULT (0) ,"PackName" TEXT,"TimesPlayed" INTEGER NOT NULL DEFAULT (0) ,"TimesFinished" INTEGER NOT NULL DEFAULT (0) ,"Unlocked" BOOL NOT NULL DEFAULT (0) ,"ParTime" FLOAT NOT NULL DEFAULT (15.0) ,"BestScore" INTEGER NOT NULL DEFAULT (0) ,"CollectibleFound" INTEGER NOT NULL DEFAULT (-1) ,"PlayTime" INTEGER NOT NULL DEFAULT (0) ,"TimesRetried" INTEGER NOT NULL DEFAULT (0) ,"IgnoreInStarCount" BOOL NOT NULL DEFAULT (0) ,"Type" INTEGER DEFAULT (0) ,"StartDate" DATETIME,"EndDate" DATETIME,"Available" BOOL NOT NULL DEFAULT (1) ,"IsBonus" BOOL NOT NULL DEFAULT (0) )

      ID                           INTEGER, PRIMARY KEY, NOT NULL
      Name                         TEXT, NOT NULL
      Filename                     TEXT, NOT NULL
      Stars                        INTEGER, NOT NULL, DEFAULT 0
      PackName                     TEXT
      TimesPlayed                  INTEGER, NOT NULL, DEFAULT 0
      TimesFinished                INTEGER, NOT NULL, DEFAULT 0
      Unlocked                     BOOL, NOT NULL, DEFAULT 0
      ParTime                      FLOAT, NOT NULL, DEFAULT 15.0
      BestScore                    INTEGER, NOT NULL, DEFAULT 0
      CollectibleFound             INTEGER, NOT NULL, DEFAULT -1
      PlayTime                     INTEGER, NOT NULL, DEFAULT 0
      TimesRetried                 INTEGER, NOT NULL, DEFAULT 0
      IgnoreInStarCount            BOOL, NOT NULL, DEFAULT 0
      Type                         INTEGER, DEFAULT 0
      StartDate                    DATETIME
      EndDate                      DATETIME
      Available                    BOOL, NOT NULL, DEFAULT 1
      IsBonus                      BOOL, NOT NULL, DEFAULT 0

## LevelPackInfo  (43 rows)

    CREATE TABLE "LevelPackInfo" ("ID" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL UNIQUE , "PackName" TEXT NOT NULL DEFAULT LP_, "Unlocked" BOOL NOT NULL DEFAULT 0, "HasPlayed" BOOL NOT NULL DEFAULT 0, "StarsRequired" INTEGER DEFAULT 30, "TileTexture" TEXT NOT NULL DEFAULT tile_world_01, "LightingColor" TEXT NOT NULL DEFAULT "255 255 255", "CurtainTexture" TEXT NOT NULL DEFAULT shower_curtain_01, "LockColor" TEXT NOT NULL DEFAULT "255 255 255", "HasAlerted" BOOL NOT NULL DEFAULT 0, "PackType" INTEGER NOT NULL DEFAULT 0, 'Hidden' BOOL NOT NULL DEFAULT 0, 'PackIcon' TEXT, 'StartDate' DATETIME, 'EndDate' DATETIME, 'Storyline' INTEGER NOT NULL DEFAULT 0, 'IAP_item_id' TEXT NOT NULL DEFAULT '', 'Bought' BOOL NOT NULL DEFAULT 0, 'DuckTextureSuffix' TEXT DEFAULT '', 'FB_AlbumName' TEXT NOT NULL DEFAULT '', 'DisplayPackName' TEXT NOT NULL DEFAULT '', "LS_Unlocked" BOOL DEFAULT 0, GrayType BOOL NOT NULL DEFAULT 0)

      ID                           INTEGER, PRIMARY KEY, NOT NULL
      PackName                     TEXT, NOT NULL, DEFAULT LP_
      Unlocked                     BOOL, NOT NULL, DEFAULT 0
      HasPlayed                    BOOL, NOT NULL, DEFAULT 0
      StarsRequired                INTEGER, DEFAULT 30
      TileTexture                  TEXT, NOT NULL, DEFAULT tile_world_01
      LightingColor                TEXT, NOT NULL, DEFAULT "255 255 255"
      CurtainTexture               TEXT, NOT NULL, DEFAULT shower_curtain_01
      LockColor                    TEXT, NOT NULL, DEFAULT "255 255 255"
      HasAlerted                   BOOL, NOT NULL, DEFAULT 0
      PackType                     INTEGER, NOT NULL, DEFAULT 0
      Hidden                       BOOL, NOT NULL, DEFAULT 0
      PackIcon                     TEXT
      StartDate                    DATETIME
      EndDate                      DATETIME
      Storyline                    INTEGER, NOT NULL, DEFAULT 0
      IAP_item_id                  TEXT, NOT NULL, DEFAULT ''
      Bought                       BOOL, NOT NULL, DEFAULT 0
      DuckTextureSuffix            TEXT, DEFAULT ''
      FB_AlbumName                 TEXT, NOT NULL, DEFAULT ''
      DisplayPackName              TEXT, NOT NULL, DEFAULT ''
      LS_Unlocked                  BOOL, DEFAULT 0
      GrayType                     BOOL, NOT NULL, DEFAULT 0

## PlayerData  (14 rows)

    CREATE TABLE "PlayerData" ("ID" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL , "EventName" TEXT NOT NULL , "EventValue" INTEGER NOT NULL , EventStringValue TEXT)

      ID                           INTEGER, PRIMARY KEY, NOT NULL
      EventName                    TEXT, NOT NULL
      EventValue                   INTEGER, NOT NULL
      EventStringValue             TEXT

## Settings  (10 rows)

    CREATE TABLE "Settings" ("Name" TEXT NOT NULL UNIQUE , "Value" INTEGER NOT NULL DEFAULT 1)

      Name                         TEXT, NOT NULL
      Value                        INTEGER, NOT NULL, DEFAULT 1

## sqlite_sequence  (3 rows)

    CREATE TABLE sqlite_sequence(name,seq)

      name                         (none)
      seq                          (none)

