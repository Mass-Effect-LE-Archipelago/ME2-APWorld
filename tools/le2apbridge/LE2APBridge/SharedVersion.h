#pragma once
// Version info for the Archipelago ME2 bridge ASI (format follows LExASIs' SharedVersion.h).

#define CURRENT_YEAR "2026"
#define DEVELOPER_A "APWorldMaker"
#define DEVELOPER_W L"APWorldMaker"
#define ASI_NAME_A "LE2 AP Bridge"
#define ASI_NAME_W L"LE2 AP Bridge"
#define ASI_NAME_NO_SPACE_A "LE2APBridge"
#define ASI_NAME_NO_SPACE_W L"LE2APBridge"
#define ASI_VERSION 1
#define ASI_PROTOCOL 1
#define ASI_DESCRIPTION "Named-pipe bridge between LE2's plot table and the Archipelago client."

#define ASI_GAME_ID_RC 5
#define ASI_GROUP_ID_RC 0

#define STRINGIFY(x) #x
#define TOSTRING(x) STRINGIFY(x)
#define VERSION_STRING_A TOSTRING(ASI_VERSION) ".0." TOSTRING(ASI_GAME_ID_RC) "." TOSTRING(ASI_GROUP_ID_RC)
#define VERSION_STRING_W TOSTRING(ASI_VERSION) L".0." TOSTRING(ASI_GAME_ID_RC) L"." TOSTRING(ASI_GROUP_ID_RC)
