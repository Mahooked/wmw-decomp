// Recovered from Walaber::Widget_Manipulator. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WALABER__WIDGET_MANIPULATOR_H
#define WMW_WALABER__WIDGET_MANIPULATOR_H

#include <stdint.h>

namespace Walaber {
struct Widget_Manipulator {
    // size 320, align 8, confidence high
    uint64_t f_0x0;
    uint8_t _pad256[248];
    uint64_t f_0x100;
    uint64_t f_0x108;
    uint8_t _pad288[16];
    int32_t f_0x120;
    uint8_t f_0x124;
    uint8_t _pad296[3];
    uint64_t f_0x128;
    double f_0x130;
    uint8_t f_0x138;
    uint8_t _pad314[1];
    uint8_t f_0x13a;
    uint8_t _tail[5];
};

}  // namespace Walaber
#endif
