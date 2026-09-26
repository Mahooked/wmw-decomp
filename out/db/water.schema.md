# water.db (221184 bytes)
# page_size=4096 encoding=UTF-8 journal=delete freelist=0 user_version=0 app_id=0

Tables: 19   views: 0   indexes: 0   triggers: 0

## ADSettings  (3 rows)

    CREATE TABLE "ADSettings" ("ScreenName" TEXT NOT NULL UNIQUE, "Show" BOOL NOT NULL, "PreferAD" TEXT NOT NULL, "Flavor" INTEGER NOT NULL, "Interval" INTEGER NOT NULL)

      ScreenName                   TEXT, NOT NULL
      Show                         BOOL, NOT NULL
      PreferAD                     TEXT, NOT NULL
      Flavor                       INTEGER, NOT NULL
      Interval                     INTEGER, NOT NULL

## Achievements  (45 rows)

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

## AllieChallengeInfo  (24 rows)

    CREATE TABLE "AllieChallengeInfo" ("ID" INTEGER PRIMARY KEY NOT NULL UNIQUE , "Available" BOOL DEFAULT 0, "IAP_item_id" TEXT, "Completed" BOOL DEFAULT 0, "LevelName" TEXT, "TimesPlayed" INTEGER DEFAULT 0, "TimesCompleted" INTEGER DEFAULT 0, "Desc" TEXT)

      ID                           INTEGER, PRIMARY KEY, NOT NULL
      Available                    BOOL, DEFAULT 0
      IAP_item_id                  TEXT
      Completed                    BOOL, DEFAULT 0
      LevelName                    TEXT
      TimesPlayed                  INTEGER, DEFAULT 0
      TimesCompleted               INTEGER, DEFAULT 0
      Desc                         TEXT

## AllieSongs  (10 rows)

    CREATE TABLE AllieSongs(ID INTEGER NOT NULL, song TEXT, unlocked BOOL DEFAULT 0, PRIMARY KEY (id))

      ID                           INTEGER, PRIMARY KEY, NOT NULL
      song                         TEXT
      unlocked                     BOOL, DEFAULT 0

## CollectibleInfo  (60 rows)

    CREATE TABLE "CollectibleInfo" ("ID" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL UNIQUE , "Unlocked" BOOL NOT NULL DEFAULT 0, "Basename" TEXT, "HasViewed" BOOL NOT NULL DEFAULT 0)

      ID                           INTEGER, PRIMARY KEY, NOT NULL
      Unlocked                     BOOL, NOT NULL, DEFAULT 0
      Basename                     TEXT
      HasViewed                    BOOL, NOT NULL, DEFAULT 0

## CommandURI  (0 rows)

    CREATE TABLE CommandURI("HeldPushCommand" TEXT)

      HeldPushCommand              TEXT

## CrankyChallengeInfo  (24 rows)

    CREATE TABLE "CrankyChallengeInfo" ("ID" INTEGER PRIMARY KEY NOT NULL UNIQUE , "Available" BOOL DEFAULT 0, "IAP_item_id" TEXT, "Completed" BOOL DEFAULT 0, "LevelName" TEXT, "LevelRequirements" TEXT, "TimesPlayed" INTEGER DEFAULT 0, "TimesCompleted" INTEGER DEFAULT 0, "Desc" TEXT)

      ID                           INTEGER, PRIMARY KEY, NOT NULL
      Available                    BOOL, DEFAULT 0
      IAP_item_id                  TEXT
      Completed                    BOOL, DEFAULT 0
      LevelName                    TEXT
      LevelRequirements            TEXT
      TimesPlayed                  INTEGER, DEFAULT 0
      TimesCompleted               INTEGER, DEFAULT 0
      Desc                         TEXT

## FoodInfo  (27 rows)

    CREATE TABLE "FoodInfo" ("ID" INTEGER PRIMARY KEY NOT NULL UNIQUE , "Basename" TEXT, "ObjectName" TEXT, "GroupName" TEXT, "Unlocked" BOOL DEFAULT 0, "HasViewed" BOOL DEFAULT 0)

      ID                           INTEGER, PRIMARY KEY, NOT NULL
      Basename                     TEXT
      ObjectName                   TEXT
      GroupName                    TEXT
      Unlocked                     BOOL, DEFAULT 0
      HasViewed                    BOOL, DEFAULT 0

## HubInfo  (5 rows)

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

## IAPInfo  (13 rows)

    CREATE TABLE "IAPInfo" ( "ID" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL UNIQUE, "Internal" TEXT NOT NULL UNIQUE, "iOS" TEXT DEFAULT '', "Google" TEXT DEFAULT '', "Amazon" TEXT DEFAULT '' )

      ID                           INTEGER, PRIMARY KEY, NOT NULL
      Internal                     TEXT, NOT NULL
      iOS                          TEXT, DEFAULT ''
      Google                       TEXT, DEFAULT ''
      Amazon                       TEXT, DEFAULT ''

## LOWInfo  (4 rows)

    CREATE TABLE LOWInfo (ID INTEGER PRIMARY KEY NOT NULL UNIQUE, Storyline INTEGER NOT NULL UNIQUE DEFAULT -1, PackName TEXT NOT NULL DEFAULT 'LP_', DisplayOrder INTEGER NOT NULL DEFAULT -1, LevelName TEXT NOT NULL DEFAULT 'LN_', DownloadDate DATETIME NOT NULL DEFAULT '1000-01-01 00:00:00', PortalTexture TEXT DEFAULT '', PlayButtonTexture TEXT DEFAULT '', BannerTexture TEXT DEFAULT '', levelStoryline INTEGER)

      ID                           INTEGER, PRIMARY KEY, NOT NULL
      Storyline                    INTEGER, NOT NULL, DEFAULT -1
      PackName                     TEXT, NOT NULL, DEFAULT 'LP_'
      DisplayOrder                 INTEGER, NOT NULL, DEFAULT -1
      LevelName                    TEXT, NOT NULL, DEFAULT 'LN_'
      DownloadDate                 DATETIME, NOT NULL, DEFAULT '1000-01-01 00:00:00'
      PortalTexture                TEXT, DEFAULT ''
      PlayButtonTexture            TEXT, DEFAULT ''
      BannerTexture                TEXT, DEFAULT ''
      levelStoryline               INTEGER

## LevelInfo  (671 rows)

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

## LevelPackInfo  (46 rows)

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

## MusicCollectInfo  (24 rows)

    CREATE TABLE MusicCollectInfo(ID INTEGER NOT NULL,Basename TEXT(25),ObjectName TEXT(25),GroupName TEXT(25),Unlocked BOOL(1),HasViewed BOOL(1), PRIMARY KEY (ID))

      ID                           INTEGER, PRIMARY KEY, NOT NULL
      Basename                     TEXT(25)
      ObjectName                   TEXT(25)
      GroupName                    TEXT(25)
      Unlocked                     BOOL(1)
      HasViewed                    BOOL(1)

## MysteryChallengeInfo  (12 rows)

    CREATE TABLE "MysteryChallengeInfo" ("ID" INTEGER PRIMARY KEY NOT NULL UNIQUE , "LevelName" TEXT, "Desc" TEXT)

      ID                           INTEGER, PRIMARY KEY, NOT NULL
      LevelName                    TEXT
      Desc                         TEXT

## PlayerData  (24 rows)

    CREATE TABLE "PlayerData" ("ID" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL , "EventName" TEXT NOT NULL , "EventValue" INTEGER NOT NULL , 'EventStringValue' TEXT)

      ID                           INTEGER, PRIMARY KEY, NOT NULL
      EventName                    TEXT, NOT NULL
      EventValue                   INTEGER, NOT NULL
      EventStringValue             TEXT

## Settings  (11 rows)

    CREATE TABLE "Settings" ("Name" TEXT NOT NULL UNIQUE , "Value" INTEGER NOT NULL DEFAULT 1)

      Name                         TEXT, NOT NULL
      Value                        INTEGER, NOT NULL, DEFAULT 1

## sqlite_sequence  (4 rows)

    CREATE TABLE sqlite_sequence(name,seq)

      name                         (none)
      seq                          (none)

## sqlite_stat1  (7 rows)

    CREATE TABLE sqlite_stat1(tbl,idx,stat)

      tbl                          (none)
      idx                          (none)
      stat                         (none)

