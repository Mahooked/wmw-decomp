// Recovered from Walaber::Widget_Group. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WALABER__WIDGET_GROUP_H
#define WMW_WALABER__WIDGET_GROUP_H

#include <stdint.h>

namespace Walaber {
struct Widget_Group {
    // size 280, align 8, confidence high
    float f_0x0;
    uint8_t _pad84[80];
    uint32_t f_0x54;
    uint8_t _pad92[4];
    uint32_t f_0x5c;
    uint8_t _pad264[168];
    uint64_t f_0x108;
    uint64_t f_0x110;
};

}  // namespace Walaber
#endif
