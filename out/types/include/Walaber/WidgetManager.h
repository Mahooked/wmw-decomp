// Recovered from Walaber::WidgetManager. Offsets and element types come from load/store
// evidence in the binary; the names do not, and are inferred
// from the accessor symbols noted against them. Everything else
// is named after the offset it sits at.
#ifndef WMW_WALABER__WIDGETMANAGER_H
#define WMW_WALABER__WIDGETMANAGER_H

#include <stdint.h>

namespace Walaber {
struct WidgetManager {
    // size 144, align 8, confidence high
    uint64_t boundingArea;  // named from getBoundingArea
    uint8_t _pad40[32];
    uint64_t f_0x28;
    uint64_t f_0x30;
    uint64_t f_0x38;
    uint64_t f_0x40;
    uint8_t customizeMode;  // named from setCustomizeMode
    uint8_t f_0x49;
    uint8_t _pad88[14];
    uint64_t f_0x58;
    uint8_t _pad112[16];
    uint8_t f_0x70;
    uint8_t _pad116[3];
    int32_t f_0x74;
    uint8_t _pad124[4];
    uint8_t f_0x7c;
    uint8_t _pad128[3];
    uint64_t f_0x80;
    uint64_t f_0x88;
};

}  // namespace Walaber
#endif
