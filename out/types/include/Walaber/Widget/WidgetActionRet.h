// Recovered from Walaber::Widget::WidgetActionRet. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WALABER__WIDGET__WIDGETACTIONRET_H
#define WMW_WALABER__WIDGET__WIDGETACTIONRET_H

#include <stdint.h>

namespace Walaber {
namespace Widget {
struct WidgetActionRet {
    // size 20, align 4, confidence high
    uint8_t f_0x0;
    uint8_t _pad12[11];
    int32_t f_0xc;
    int32_t f_0x10;
};

}  // namespace Walaber::Widget
#endif
