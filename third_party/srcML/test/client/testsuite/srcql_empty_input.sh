#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-only
#
# @file srcql_empty_input.sh
#
# @copyright Copyright (C) 2013-2024 srcML, LLC. (www.srcML.org)

# test framework
source $(dirname "$0")/framework_test.sh

# test
defineXML srcql_error <<- 'STDOUT'
	Error Parsing: Start tag expected, '<' not found
STDOUT

defineXML srcql_empty <<- 'STDOUT'
	<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
	<unit xmlns="http://www.srcML.org/srcML/src" revision="REVISION">

	<unit revision="REVISION" language="C++"/>

	</unit>
STDOUT

createfile sub/a.cpp.xml ""

srcml --srcql='FIND src:unit' sub/a.cpp.xml
check_exit 1

srcml -l C++ --srcql='FIND src:unit' sub/a.cpp.xml -o sub/b.cpp.xml
check_exit 1

srcml -l C++ --srcql='FIND src:unit' -o sub/b.cpp.xml sub/a.cpp.xml
check_exit 1
