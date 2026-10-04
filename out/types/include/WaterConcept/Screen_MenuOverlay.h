// Recovered from WaterConcept::Screen_MenuOverlay. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WATERCONCEPT__SCREEN_MENUOVERLAY_H
#define WMW_WATERCONCEPT__SCREEN_MENUOVERLAY_H

#include <stdint.h>

namespace WaterConcept {
struct Screen_MenuOverlay {
    // size 160, align 8, confidence high
    uint64_t f_0x0;
    uint8_t _pad16[8];
    uint64_t f_0x10;
    uint8_t _pad148[124];
    uint8_t f_0x94;
    uint8_t f_0x95;
    uint8_t _pad152[2];
    float f_0x98;
    uint8_t _tail[4];
};

}  // namespace WaterConcept
#endif
