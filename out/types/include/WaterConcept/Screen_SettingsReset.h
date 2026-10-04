// Recovered from WaterConcept::Screen_SettingsReset. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WATERCONCEPT__SCREEN_SETTINGSRESET_H
#define WMW_WATERCONCEPT__SCREEN_SETTINGSRESET_H

#include <stdint.h>

namespace WaterConcept {
struct Screen_SettingsReset {
    // size 280, align 8, confidence high
    uint64_t f_0x0;
    uint8_t _pad16[8];
    uint64_t f_0x10;
    uint8_t _pad32[8];
    uint64_t f_0x20;
    uint8_t _pad144[104];
    uint64_t f_0x90;
    uint8_t _pad156[4];
    uint32_t f_0x9c;
    uint8_t _pad164[4];
    uint8_t f_0xa4;
    uint8_t _pad172[7];
    uint8_t f_0xac;
    uint8_t _pad176[3];
    uint64_t f_0xb0;
    int32_t f_0xb8;
    int32_t f_0xbc;
    int32_t f_0xc0;
    uint8_t _pad200[4];
    uint64_t f_0xc8;
    uint8_t _pad216[8];
    float f_0xd8;
    uint8_t f_0xdc;
    uint8_t _pad224[3];
    int32_t f_0xe0;
    uint8_t f_0xe4;
    uint8_t _pad232[3];
    uint64_t f_0xe8;
    uint8_t _pad248[8];
    uint64_t f_0xf8;
    uint64_t f_0x100;
    uint8_t _pad272[8];
    float f_0x110;
    uint8_t f_0x114;
    uint8_t _tail[3];
};

}  // namespace WaterConcept
#endif
