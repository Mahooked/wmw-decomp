// Recovered from WaterConcept::Screen_SettingsProfile. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WATERCONCEPT__SCREEN_SETTINGSPROFILE_H
#define WMW_WATERCONCEPT__SCREEN_SETTINGSPROFILE_H

#include <stdint.h>

namespace WaterConcept {
struct Screen_SettingsProfile {
    // size 248, align 8, confidence high
    uint64_t f_0x0;
    uint8_t _pad16[8];
    uint64_t f_0x10;
    uint8_t _pad32[8];
    uint64_t f_0x20;
    uint8_t _pad144[104];
    uint64_t f_0x90;
    uint8_t _pad156[4];
    uint32_t f_0x9c;
    uint8_t _pad168[8];
    uint64_t f_0xa8;
    uint64_t f_0xb0;
    uint8_t _pad192[8];
    uint64_t f_0xc0;
    double f_0xc8;
    uint64_t f_0xd0;
    uint8_t _pad224[8];
    uint8_t f_0xe0;
    uint8_t _pad228[3];
    float f_0xe4;
    uint8_t f_0xe8;
    uint8_t _pad236[3];
    int32_t f_0xec;
    float f_0xf0;
    uint8_t _tail[4];
};

}  // namespace WaterConcept
#endif
