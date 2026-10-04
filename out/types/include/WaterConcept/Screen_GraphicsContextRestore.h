// Recovered from WaterConcept::Screen_GraphicsContextRestore. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WATERCONCEPT__SCREEN_GRAPHICSCONTEXTRESTORE_H
#define WMW_WATERCONCEPT__SCREEN_GRAPHICSCONTEXTRESTORE_H

#include <stdint.h>

namespace WaterConcept {
struct Screen_GraphicsContextRestore {
    // size 168, align 8, confidence high
    uint64_t f_0x0;
    uint8_t _pad13[5];
    uint8_t f_0xd;
    uint8_t _pad16[2];
    uint64_t f_0x10;
    uint8_t _pad144[120];
    uint64_t f_0x90;
    uint64_t f_0x98;
    uint8_t f_0xa0;
    uint8_t _tail[7];
};

}  // namespace WaterConcept
#endif
