// Recovered from WaterConcept::Screen_EditorObjectSelect. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WATERCONCEPT__SCREEN_EDITOROBJECTSELECT_H
#define WMW_WATERCONCEPT__SCREEN_EDITOROBJECTSELECT_H

#include <stdint.h>

namespace WaterConcept {
struct Screen_EditorObjectSelect {
    // size 208, align 8, confidence high
    uint64_t f_0x0;
    uint8_t _pad16[8];
    uint64_t f_0x10;
    uint8_t _pad32[8];
    uint64_t f_0x20;
    uint8_t _pad144[104];
    uint64_t f_0x90;
    uint8_t _pad160[8];
    uint64_t f_0xa0;
    uint64_t f_0xa8;
    uint64_t f_0xb0;
    uint64_t f_0xb8;
    float f_0xc0;
    float f_0xc4;
    float f_0xc8;
    float f_0xcc;
};

}  // namespace WaterConcept
#endif
