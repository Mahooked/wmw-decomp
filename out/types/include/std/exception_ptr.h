// Recovered from std::exception_ptr. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_STD__EXCEPTION_PTR_H
#define WMW_STD__EXCEPTION_PTR_H

#include <stdint.h>

namespace std {
struct exception_ptr {
    // size 8, align 8, confidence high
    uint64_t f_0x0;
};

}  // namespace std
#endif
