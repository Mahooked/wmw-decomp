// Recovered from WaterConcept::Screen_Editor::ObjectData. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WATERCONCEPT__SCREEN_EDITOR__OBJECTDATA_H
#define WMW_WATERCONCEPT__SCREEN_EDITOR__OBJECTDATA_H

#include <stdint.h>

namespace WaterConcept {
namespace Screen_Editor {
struct ObjectData {
    // size 120, align 8, confidence high
    uint8_t _pad24[24];
    uint64_t f_0x18;
    uint8_t _pad80[48];
    uint8_t f_0x50;
    uint8_t _pad88[7];
    uint64_t f_0x58;
    uint64_t f_0x60;
    uint8_t _pad112[8];
    uint64_t f_0x70;
};

}  // namespace WaterConcept::Screen_Editor
#endif
