#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-only
#
# @file srcql_warning.sh
#
# @copyright Copyright (C) 2025 srcML, LLC. (www.srcML.org)

# test framework
source $(dirname "$0")/framework_test.sh

defineXML empty <<- 'STDOUT'
	<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
	<unit xmlns="http://www.srcML.org/srcML/src" revision="REVISION"/>
STDOUT

defineXML srcml <<- 'STDOUT'
	<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
	<unit xmlns="http://www.srcML.org/srcML/src" revision="1.0.0">

	<unit revision="1.0.0" language="C++" item="1"><decl><type><name>int</name></type> <name>n</name></decl></unit>

	</unit>
STDOUT

define error <<- 'STDOUT'
	\033[31msrcml: WARNING The srcql query 'FIND int '
	does not contain a srcql logical variable that starts with a \033[1m$\033[0m.
	\033[31mIf your srcql query was meant to contain a logical variable, then enclose the
	entire query in single quotes, not double quotes, to prevent shell variable
	expansion. If not, you can safely ignore this message or disable it with the
	option \033[1;31m--srcql-warning-off\033[0m \033[31mor \033[1;31m-F\033[0m\033[31m.\033[0m

STDOUT

srcml --text="int n;" -l C++ --srcql='FIND $T $A'
check "$srcml"

srcml --text="int n;" -l C++ --srcql='FIND $T $A' --srcql-warning-off
check "$srcml"

srcml --text="int n;" -l C++ --srcql='FIND $T $A' -F
check "$srcml"

srcml --text="int n;" -l C++ --srcql="FIND int $A"
check "$empty" "$error"

srcml --text="int n;" -l C++ --srcql="FIND int $A" --srcql-warning-off
check "$empty"

srcml --text="int n;" -l C++ --srcql="FIND int $A" -F
check "$empty"
