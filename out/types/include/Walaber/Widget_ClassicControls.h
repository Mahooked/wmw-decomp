// Recovered from Walaber::Widget_ClassicControls. Offsets and element types come from load/store
// evidence in the binary; the names do not, and are inferred
// from the accessor symbols noted against them. Everything else
// is named after the offset it sits at.
#ifndef WMW_WALABER__WIDGET_CLASSICCONTROLS_H
#define WMW_WALABER__WIDGET_CLASSICCONTROLS_H

#include <stdint.h>

namespace Walaber {
struct Widget_ClassicControls {
    // size 272, align 8, confidence high
    uint8_t _pad256[256];
    uint64_t mainFingerPos;  // named from getMainFingerPos
    uint64_t f_0x108;
};

}  // namespace Walaber
#endif
