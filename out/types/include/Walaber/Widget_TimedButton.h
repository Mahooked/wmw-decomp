// Recovered from Walaber::Widget_TimedButton. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WALABER__WIDGET_TIMEDBUTTON_H
#define WMW_WALABER__WIDGET_TIMEDBUTTON_H

#include <stdint.h>

namespace Walaber {
struct Widget_TimedButton {
    // size 352, align 8, confidence high
    uint64_t f_0x0;
    uint8_t _pad288[280];
    double f_0x120;
    double f_0x128;
    double f_0x130;
    double f_0x138;
    uint8_t f_0x140;
    uint8_t f_0x141;
    uint8_t _pad324[2];
    float f_0x144;
    float f_0x148;
    uint8_t _pad340[8];
    int32_t f_0x154;
    uint8_t f_0x158;
    uint8_t _tail[7];
};

}  // namespace Walaber
#endif
