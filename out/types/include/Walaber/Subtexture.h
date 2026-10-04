// Recovered from Walaber::Subtexture. Offsets and element types come from load/store
// evidence in the binary; the names do not, and are inferred
// from the accessor symbols noted against them. Everything else
// is named after the offset it sits at.
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
    uint64_t isTextureParent;  // named from isTextureParent
};

}  // namespace Walaber
#endif
