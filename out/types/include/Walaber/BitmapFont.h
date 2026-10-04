// Recovered from Walaber::BitmapFont. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WALABER__BITMAPFONT_H
#define WMW_WALABER__BITMAPFONT_H

#include <stdint.h>

namespace Walaber {
struct BitmapFont {
    // size 168, align 8, confidence high
    uint64_t f_0x0;
    uint8_t _pad24[16];
    uint64_t f_0x18;
    uint64_t f_0x20;
    uint8_t _pad48[8];
    uint64_t f_0x30;
    uint64_t f_0x38;
    uint8_t _pad80[16];
    uint64_t f_0x50;
    uint8_t _pad120[32];
    uint64_t f_0x78;
    uint64_t f_0x80;
    uint64_t f_0x88;
    uint8_t _pad148[4];
    float f_0x94;
    float f_0x98;
    int32_t f_0x9c;
    int32_t f_0xa0;
    uint8_t _tail[4];
};

}  // namespace Walaber
#endif
