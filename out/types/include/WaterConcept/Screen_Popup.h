// Recovered from WaterConcept::Screen_Popup. Offsets and element types come from load/store
// evidence in the binary; the names do not, and are inferred
// from the accessor symbols noted against them. Everything else
// is named after the offset it sits at.
#ifndef WMW_WATERCONCEPT__SCREEN_POPUP_H
#define WMW_WATERCONCEPT__SCREEN_POPUP_H

#include <stdint.h>

namespace WaterConcept {
struct Screen_Popup {
    // size 1440, align 8, confidence high
    uint8_t f_0x0;
    uint8_t _pad16[15];
    uint64_t stageTranslation;  // named from getStageTranslation
    uint8_t _pad188[164];
    int32_t f_0xbc;
    uint8_t _pad228[36];
    int32_t f_0xe4;
    uint8_t _pad680[448];
    int32_t f_0x2a8;
    uint8_t _pad736[52];
    int32_t f_0x2e0;
    uint8_t _pad780[40];
    int32_t f_0x30c;
    int32_t f_0x310;
    uint8_t _pad840[52];
    float f_0x348;
    uint8_t f_0x34c;
    uint8_t _pad1120[275];
    uint64_t f_0x460;
    uint64_t f_0x468;
    uint8_t _pad1168[32];
    uint8_t f_0x490;
    uint8_t _pad1224[55];
    uint64_t f_0x4c8;
    uint8_t _pad1248[16];
    uint8_t f_0x4e0;
    uint8_t _pad1344[95];
    uint8_t f_0x540;
    uint8_t _pad1432[87];
    uint64_t f_0x598;
};

}  // namespace WaterConcept
#endif
