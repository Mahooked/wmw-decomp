// Recovered from Walaber::Subtexture. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WALABER__SUBTEXTURE_H
#define WMW_WALABER__SUBTEXTURE_H

#include <stdint.h>

namespace Walaber {
struct Subtexture {
    // size 232, align 8, confidence high
    uint64_t f_0x0;
    uint8_t _pad120[112];
    int32_t f_0x78;
    uint8_t _pad192[68];
    uint64_t f_0xc0;
    uint8_t _pad208[8];
    uint8_t f_0xd0;
    uint8_t _pad224[15];
    uint64_t f_0xe0;
};

}  // namespace Walaber
#endif
