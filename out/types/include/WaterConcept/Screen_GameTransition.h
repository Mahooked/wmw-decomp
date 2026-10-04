// Recovered from WaterConcept::Screen_GameTransition. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WATERCONCEPT__SCREEN_GAMETRANSITION_H
#define WMW_WATERCONCEPT__SCREEN_GAMETRANSITION_H

#include <stdint.h>

namespace WaterConcept {
struct Screen_GameTransition {
    // size 168, align 8, confidence high
    uint8_t _pad16[16];
    uint64_t f_0x10;
    uint8_t _pad156[132];
    int32_t f_0x9c;
    uint8_t f_0xa0;
    uint8_t f_0xa1;
    uint8_t _tail[6];
};

}  // namespace WaterConcept
#endif
