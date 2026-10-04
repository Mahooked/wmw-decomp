// Recovered from Walaber::Widget_FingerCatcher. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WALABER__WIDGET_FINGERCATCHER_H
#define WMW_WALABER__WIDGET_FINGERCATCHER_H

#include <stdint.h>

namespace Walaber {
struct Widget_FingerCatcher {
    // size 336, align 8, confidence high
    uint64_t f_0x0;
    uint8_t _pad256[248];
    uint64_t f_0x100;
    uint64_t f_0x108;
    uint64_t f_0x110;
    uint64_t f_0x118;
    uint64_t f_0x120;
    uint8_t _pad304[8];
    uint64_t f_0x130;
    uint64_t f_0x138;
    uint64_t f_0x140;
    uint8_t f_0x148;
    uint8_t _tail[7];
};

}  // namespace Walaber
#endif
