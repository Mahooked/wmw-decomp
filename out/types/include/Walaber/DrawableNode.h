// Recovered from Walaber::DrawableNode. Offsets and element types come from load/store
// evidence in the binary; the names do not, and are inferred
// from the accessor symbols noted against them. Everything else
// is named after the offset it sits at.
#ifndef WMW_WALABER__DRAWABLENODE_H
#define WMW_WALABER__DRAWABLENODE_H

#include <stdint.h>

namespace Walaber {
struct DrawableNode {
    // size 132, align 4, confidence high
    uint8_t _pad128[128];
    int32_t layer;  // named from setLayer
};

}  // namespace Walaber
#endif
