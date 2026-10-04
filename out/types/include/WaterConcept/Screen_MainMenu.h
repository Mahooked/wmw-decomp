// Recovered from WaterConcept::Screen_MainMenu. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WATERCONCEPT__SCREEN_MAINMENU_H
#define WMW_WATERCONCEPT__SCREEN_MAINMENU_H

#include <stdint.h>

namespace WaterConcept {
struct Screen_MainMenu {
    // size 712, align 8, confidence high
    int32_t f_0x0;
    uint8_t f_0x4;
    uint8_t _pad16[11];
    uint64_t f_0x10;
    uint8_t _pad32[8];
    uint64_t f_0x20;
    uint8_t _pad169[129];
    uint8_t f_0xa9;
    uint8_t _pad188[18];
    uint32_t f_0xbc;
    uint8_t _pad196[4];
    uint32_t f_0xc4;
    uint8_t _pad232[32];
    uint64_t f_0xe8;
    int32_t f_0xf0;
    uint8_t _pad264[20];
    uint64_t f_0x108;
    uint8_t _pad328[56];
    uint8_t f_0x148;
    uint8_t _pad336[7];
    float f_0x150;
    uint8_t _pad520[180];
    float f_0x208;
    float f_0x20c;
    float f_0x210;
    uint8_t _pad544[12];
    int32_t f_0x220;
    uint8_t _pad560[12];
    uint64_t f_0x230;
    uint8_t _pad588[20];
    int32_t f_0x24c;
    uint8_t f_0x250;
    uint8_t _pad600[7];
    uint64_t f_0x258;
    uint8_t _pad632[24];
    int32_t f_0x278;
    uint8_t _pad640[4];
    uint64_t f_0x280;
    uint8_t _pad696[48];
    uint64_t f_0x2b8;
    uint8_t f_0x2c0;
    uint8_t _pad708[3];
    int32_t f_0x2c4;
};

}  // namespace WaterConcept
#endif
