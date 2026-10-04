// Recovered from Walaber::DrawableNode. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WALABER__DRAWABLENODE_H
#define WMW_WALABER__DRAWABLENODE_H

#include <stdint.h>

namespace Walaber {
struct DrawableNode {
    // size 132, align 4, confidence high
    uint8_t _pad128[128];
    int32_t f_0x80;
};

}  // namespace Walaber
#endif
