// SPDX-License-Identifier: GPL-3.0-only
/**
 * @file srcml_options.hpp
 *
 * @copyright Copyright (C) 2014-2024 srcML, LLC. (www.srcML.org)
 *
 * This file is part of the srcml command-line client.
 */

#ifndef SRCML_OPTIONS_HPP
#define SRCML_OPTIONS_HPP

#include <cstdint>

class SRCMLOptions {
public:
    friend void enable(unsigned long long option);

    static void set(unsigned long long options) {

        opt = options;
    }

    static uint_fast64_t get()  {

        return opt;
    }

 private:
    static uint_fast64_t opt;
};

inline bool option(unsigned long long option) {

    return SRCMLOptions::get() & option;
}

inline void enable(unsigned long long option) {

    SRCMLOptions::opt |= option;
}

#endif
