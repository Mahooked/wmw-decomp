// Recovered from std::runtime_error. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_STD__RUNTIME_ERROR_H
#define WMW_STD__RUNTIME_ERROR_H

#include <stdint.h>

namespace std {
struct runtime_error {
    // size 16, align 8, confidence high
    uint64_t f_0x0;
    uint64_t f_0x8;
};

}  // namespace std
#endif
