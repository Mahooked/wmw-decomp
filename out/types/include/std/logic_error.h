// Recovered from std::logic_error. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_STD__LOGIC_ERROR_H
#define WMW_STD__LOGIC_ERROR_H

#include <stdint.h>

namespace std {
struct logic_error {
    // size 16, align 8, confidence high
    uint64_t f_0x0;
    uint64_t f_0x8;
};

}  // namespace std
#endif
