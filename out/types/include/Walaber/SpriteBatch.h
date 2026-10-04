// Recovered from Walaber::SpriteBatch. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WALABER__SPRITEBATCH_H
#define WMW_WALABER__SPRITEBATCH_H

#include <stdint.h>

namespace Walaber {
struct SpriteBatch {
    // size 56, align 8, confidence high
    uint64_t f_0x0;
    uint8_t _pad24[16];
    int32_t f_0x18;
    int32_t f_0x1c;
    int32_t f_0x20;
    int32_t f_0x24;
    int32_t f_0x28;
    uint8_t _pad48[4];
    uint64_t f_0x30;
};

}  // namespace Walaber
#endif
