#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-only
#
# @file xpath_element_unit.sh
#
# @copyright Copyright (C) 2013-2024 srcML, LLC. (www.srcML.org)

# test framework
source $(dirname "$0")/framework_test.sh

# test setting the attribute on xpath query results
defineXML resultstdin <<- 'STDOUT'
	<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
	<unit xmlns="http://www.srcML.org/srcML/src" xmlns:pre="foo.com" revision="REVISION" language="C++"><expr_stmt><expr><pre:element><name>a</name></pre:element></expr>;</expr_stmt>
	</unit>
STDOUT

# test setting the attribute on xpath query results
defineXML result <<- 'STDOUT'
	<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
	<unit xmlns="http://www.srcML.org/srcML/src" xmlns:pre="foo.com" revision="REVISION" language="C++" filename="sub/a.cpp"><expr_stmt><expr><pre:element><name>a</name></pre:element></expr>;</expr_stmt>
	</unit>
STDOUT

createfile sub/a.cpp "a;
"
srcml sub/a.cpp --xmlns:pre=foo.com -o sub/a.xml

# from a file
srcml sub/a.xml --xpath="//src:name" --element="pre:element" --xmlns:pre=foo.com
check "$result"

srcml --xpath="//src:name" sub/a.xml --element="pre:element" --xmlns:pre=foo.com
check "$result"

# from standard input
echo "a;" | srcml -l C++ --xmlns:pre=foo.com --xpath="//src:name" --element="pre:element" --xmlns:pre=foo.com
check "$resultstdin"

# output to a file
srcml sub/a.xml --xpath="//src:name" --element="pre:element" --xmlns:pre=foo.com -o result.xml
check result.xml "$result"

srcml --xpath="//src:name" sub/a.xml --element="pre:element" --xmlns:pre=foo.com -o result.xml
check result.xml "$result"

echo "a;" | srcml -l C++  --xmlns:pre=foo.com --xpath="//src:name" --element="pre:element" --xmlns:pre=foo.com -o result.xml
check result.xml "$resultstdin"

# Test for both element and attribute
defineXML prefix <<- 'STDOUT'
	<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
	<unit xmlns="http://www.srcML.org/srcML/src" xmlns:extra="mlcollard.net/extr" revision="1.0.0" language="Java" filename="a.java">
	<expr_stmt><expr><extra:state extra:type="test"><name>a</name></extra:state> <operator>=</operator> <extra:state extra:type="test"><name>b</name></extra:state></expr>;</expr_stmt>
	</unit>
STDOUT
srcml -l Java --filename="a.java" --text="\na = b;\n" --xpath="//src:name" --xmlns:extra="mlcollard.net/extr" --element=extra:state --attribute extra:type=test
check "$prefix"

defineXML prefixdiff <<- 'STDOUT'
	<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
	<unit xmlns="http://www.srcML.org/srcML/src" xmlns:attr="mlcollard.net/attr" xmlns:extra="mlcollard.net/extr" revision="1.0.0" language="Java" filename="a.java">
	<expr_stmt><expr><extra:state extra:type="test"><name>a</name></extra:state> <operator>=</operator> <extra:state extra:type="test"><name>b</name></extra:state></expr>;</expr_stmt>
	</unit>
STDOUT
srcml -l Java --filename="a.java" --text="\na = b;\n" --xpath="//src:name" --xmlns:extra="mlcollard.net/extr" --xmlns:attr="mlcollard.net/attr" --element=extra:state --attribute attr:type=test
check "$prefixdiff"
