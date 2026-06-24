#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-only
#
# @file srcql_element_archive.sh
#
# @copyright Copyright (C) 2013-2024 srcML, LLC. (www.srcML.org)

# test framework
source $(dirname "$0")/framework_test.sh

# test setting the attribute on srcql query results
defineXML result <<- 'STDOUT'
	<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
	<unit xmlns="http://www.srcML.org/srcML/src" xmlns:pre="foo.com" revision="REVISION">

	<unit revision="REVISION" language="C++" filename="a.cpp" hash="aa2a72b26cf958d8718a2e9bc6b84679a81d54cb"><expr_stmt><pre:element><expr><name>a</name></expr></pre:element>;</expr_stmt>
	</unit>

	<unit revision="REVISION" language="C++" filename="b.cpp" hash="520b48acbdb61e411641fd94359a82686d5591eb"><expr_stmt><pre:element><expr><name>b</name></expr></pre:element>;</expr_stmt>
	</unit>

	</unit>
STDOUT

createfile a.cpp "a;
"
createfile b.cpp "b;
"

srcml a.cpp b.cpp --xmlns:pre=foo.com -o archive.xml

# from a file
srcml archive.xml --srcql='FIND $N' --element="pre:element" --xmlns:pre=foo.com
check "$result"

srcml --srcql='FIND $N' archive.xml --element="pre:element" --xmlns:pre=foo.com
check "$result"

# output to a file
srcml archive.xml --srcql='FIND $N' --element="pre:element" --xmlns:pre=foo.com -o result.xml
check result.xml "$result"

srcml --srcql='FIND $N' archive.xml --element="pre:element" --xmlns:pre=foo.com -o result.xml
check result.xml "$result"
