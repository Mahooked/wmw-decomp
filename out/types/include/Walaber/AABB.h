// Recovered from Walaber::AABB. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WALABER__AABB_H
#define WMW_WALABER__AABB_H

#include <stdint.h>

namespace Walaber {
struct AABB {
    // size 20, align 4, confidence high
    float f_0x0;
    float f_0x4;
    float f_0x8;
    float f_0xc;
    int32_t f_0x10;
};

}  // namespace Walaber
#endif
