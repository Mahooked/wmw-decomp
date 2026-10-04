// Recovered from WaterConcept::InteractiveObject. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WATERCONCEPT__INTERACTIVEOBJECT_H
#define WMW_WATERCONCEPT__INTERACTIVEOBJECT_H

#include <stdint.h>

namespace WaterConcept {
struct InteractiveObject {
    // size 712, align 8, confidence high
    uint64_t f_0x0;
    uint8_t _pad216[208];
    int32_t f_0xd8;
    uint8_t _pad224[4];
    uint64_t f_0xe0;
    uint64_t f_0xe8;
    uint8_t _pad248[8];
    uint64_t f_0xf8;
    uint64_t f_0x100;
    uint8_t _pad296[32];
    double f_0x128;
    uint8_t _pad384[80];
    uint64_t f_0x180;
    uint8_t _pad400[8];
    uint64_t f_0x190;
    uint8_t _pad616[208];
    uint64_t f_0x268;
    uint64_t f_0x270;
    uint8_t _pad640[8];
    uint8_t f_0x280;
    uint8_t _pad680[39];
    int32_t f_0x2a8;
    uint8_t _pad708[24];
    uint8_t f_0x2c4;
    uint8_t _tail[3];
};

}  // namespace WaterConcept
#endif
