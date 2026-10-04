// Recovered from Walaber::ProgrammaticTexture2D. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WALABER__PROGRAMMATICTEXTURE2D_H
#define WMW_WALABER__PROGRAMMATICTEXTURE2D_H

#include <stdint.h>

namespace Walaber {
struct ProgrammaticTexture2D {
    // size 136, align 8, confidence high
    uint64_t f_0x0;
    uint8_t _pad52[44];
    int32_t f_0x34;
    uint8_t _pad120[64];
    int32_t f_0x78;
    int32_t f_0x7c;
    int32_t f_0x80;
    uint8_t _tail[4];
};

}  // namespace Walaber
#endif
