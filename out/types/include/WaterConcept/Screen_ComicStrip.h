// Recovered from WaterConcept::Screen_ComicStrip. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WATERCONCEPT__SCREEN_COMICSTRIP_H
#define WMW_WATERCONCEPT__SCREEN_COMICSTRIP_H

#include <stdint.h>

namespace WaterConcept {
struct Screen_ComicStrip {
    // size 168, align 8, confidence high
    uint8_t _pad16[16];
    uint64_t f_0x10;
    uint8_t _pad152[128];
    uint64_t f_0x98;
    uint8_t f_0xa0;
    uint8_t _tail[7];
};

}  // namespace WaterConcept
#endif
