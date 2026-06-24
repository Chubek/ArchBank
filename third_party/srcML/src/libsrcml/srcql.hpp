// SPDX-License-Identifier: GPL-3.0-only
/**
 * @file srcql.hpp
 *
 * @copyright Copyright (C) 2023 srcML, LLC. (www.srcML.org)
 */

#ifndef SRCQL_HPP
#define SRCQL_HPP

#define SRCQL_VERSION_NUMBER 10000
#define SRCQL_VERSION_STRING "1.0.0"

// The current version of srcQL as a number
int srcql_version_number();

// The current version of srcQL as a string
const char* srcql_version_string();

// srcQuery -> XPath
const char* srcql_convert_query_to_xpath(const char* src_query, const char* language);


#endif
