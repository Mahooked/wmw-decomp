// Recovered from Walaber::Widget_IconList::Icon. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WALABER__WIDGET_ICONLIST__ICON_H
#define WMW_WALABER__WIDGET_ICONLIST__ICON_H

#include <stdint.h>

namespace Walaber {
namespace Widget_IconList {
struct Icon {
    // size 48, align 8, confidence high
    uint64_t f_0x0;
    uint8_t _pad40[32];
    int32_t f_0x28;
    uint8_t _tail[4];
};

}  // namespace Walaber::Widget_IconList
#endif
